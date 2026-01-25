"""Compressed static files app using content-addressable storage.

Files are pre-compressed at startup and served via hash-based URLs for optimal caching.

Install with: uv add "muxy[compress]"

This should be refactored once Granian's static files supports serving compressed
sidecar files (https://github.com/emmett-framework/granian/issues/577).
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler

try:
    from cramjam import (
        brotli,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
        gzip,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
        zstd,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    )
except ImportError as e:
    msg = (
        "Static files app requires the 'compress' extra. "
        "Install with: uv add 'muxy[compress]'"
    )
    raise ImportError(msg) from e


type Encoding = Literal["zstd", "br", "gzip"]
type UrlPathFn = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class FileVariant:
    """A compressed variant of a static file."""

    path_str: str  # Path to file on disk (as string for response_file)
    encoding: str  # "zstd", "br", "gzip", or "identity"
    size: int  # File size in bytes


@dataclass(frozen=True, slots=True)
class FileEntry:
    """A static file with its variants."""

    content_type: str  # MIME type
    content_hash: str  # SHA256 hash (first 8 chars)
    variants: dict[str, FileVariant]  # encoding -> FileVariant
    # Precomputed at startup for fast request handling
    url: str  # e.g., "/styles.a1b2c3d4.css"
    path_stem: str  # e.g., "styles" or "css/app" (without extension)


@dataclass(slots=True)
class _BuildStats:
    """Stats collected during file processing."""

    files_total: int = 0
    files_compressed: int = 0  # Files that got at least one compressed variant
    variants_created: int = 0  # New compressed files written
    variants_reused: int = 0  # Existing compressed files reused
    variants_skipped: int = 0  # Compression skipped (larger than original)
    original_bytes: int = 0  # Total size of original files
    compressed_bytes: int = 0  # Total size of compressed variants used


DEFAULT_COMPRESSIBLE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".css",
        ".js",
        ".mjs",
        ".cjs",
        ".html",
        ".htm",
        ".xml",
        ".svg",
        ".json",
        ".map",
        ".txt",
        ".md",
        ".wasm",
    }
)

# File extensions for pre-compressed files (skip during scanning)
_COMPRESSED_SUFFIXES: frozenset[str] = frozenset({".zst", ".br", ".gz"})

# Encoding name to file suffix mapping
_ENCODING_SUFFIXES: dict[str, str] = {"zstd": ".zst", "br": ".br", "gzip": ".gz"}

# Max compression levels for each encoding
_MAX_LEVELS: dict[str, int] = {"zstd": 22, "br": 11, "gzip": 9}


def _compress_file(data: bytes, encoding: str) -> bytes:
    """Compress data with the given encoding at max level."""
    level = _MAX_LEVELS[encoding]
    if encoding == "zstd":
        return bytes(zstd.compress(data, level=level))
    elif encoding == "br":
        return bytes(brotli.compress(data, level=level))
    else:  # gzip
        return bytes(gzip.compress(data, level=level))


def _get_content_type(path: Path) -> str:
    """Guess MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def _parse_accept_encoding(header: str) -> list[tuple[str, float]]:
    """Parse Accept-Encoding header and return encodings with quality values."""
    encodings: list[tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        q_idx = part.find(";q=")
        if q_idx == -1:  # no quality value
            encodings.append((part.lower(), 1.0))
        else:
            try:
                quality = float(part[q_idx + 3 :])
            except ValueError:
                quality = 1.0
            encodings.append((part[:q_idx].strip().lower(), quality))
    return encodings


def _select_encoding(
    accept_encoding: str | None,
    server_priority: dict[str, int],
    available_encodings: Iterable[str],
) -> str:
    """Select best available encoding based on Accept-Encoding header.

    When client qualities are equal, uses server priority order.
    Falls back to "identity" if no acceptable encoding.
    """
    if accept_encoding is None:
        return "identity"

    client_encodings = _parse_accept_encoding(accept_encoding)

    # Handle wildcard and explicit encodings
    wildcard_quality = 0.0
    explicit: dict[str, float] = {}
    for name, quality in client_encodings:
        if name == "*":
            wildcard_quality = quality
        else:
            explicit[name] = quality

    # Build list of supported encodings with their qualities
    supported: list[tuple[str, float, int]] = []
    for enc in available_encodings:
        if enc == "identity":
            continue  # Handle identity separately as fallback
        if enc in explicit:
            quality = explicit[enc]
        elif wildcard_quality > 0:
            quality = wildcard_quality
        else:
            continue
        if quality > 0:
            priority = server_priority.get(enc, 999)
            supported.append((enc, quality, priority))

    if not supported:
        return "identity"

    # Sort by quality descending, then by server priority ascending
    supported.sort(key=lambda x: (-x[1], x[2]))
    return supported[0][0]


def _build_file_entries(
    directory: Path,
    encodings: tuple[str, ...],
    compressible_extensions: frozenset[str],
    outdir: Path | None = None,
) -> tuple[dict[str, str], dict[str, FileEntry], dict[str, FileEntry], _BuildStats]:
    """Walk directory and build file entries with compressed variants.

    Args:
        directory: Source directory containing static files
        encodings: Compression encodings to use
        compressible_extensions: File extensions to compress
        outdir: Optional output directory for CAS files. If None, files are
            written alongside originals in the source directory.

    Returns:
        (path_to_url, hash_to_entry, path_to_entry, stats) tuple
    """
    path_to_url: dict[str, str] = {}
    hash_to_entry: dict[str, FileEntry] = {}
    path_to_entry: dict[str, FileEntry] = {}
    stats = _BuildStats()

    # SECURITY: followlinks=True allows symlinks to be indexed at startup.
    # This is safe from path traversal (requests only do dict lookups, not fs
    # access). Note that it's up to the user to ensure the directory doesn't
    # contain symlinks to sensitive locations, as those files would be indexed
    # and served. This is considered safe because just as it's the user's
    # responsibility not to include sensitive files in the static files dir,
    # they also shouldn't be including symlinks to sensitive files.
    for dirpath, _dirnames, filenames in os.walk(directory, followlinks=True):
        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Skip existing compressed files
            if file_path.suffix in _COMPRESSED_SUFFIXES:
                continue

            # Compute relative path and stem (without extension)
            rel_path = file_path.relative_to(directory)
            rel_path_str = str(rel_path)
            path_stem = str(rel_path.with_suffix(""))
            ext = file_path.suffix

            # Read file and compute hash
            content = file_path.read_bytes()
            content_hash = hashlib.sha256(content).hexdigest()[:8]

            # Track stats
            stats.files_total += 1
            stats.original_bytes += len(content)

            # Precompute URL (uses hashed filename)
            hashed_filename = f"{path_stem}.{content_hash}{ext}"
            url = f"/{hashed_filename}"

            # Determine output base path for variants
            if outdir is not None:
                # Output to separate directory with hashed filename
                out_base = outdir / hashed_filename
                out_base.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Output alongside original (no hashed filename for identity)
                out_base = None

            # Create identity variant
            if outdir is not None:
                # Copy original to outdir with hashed name
                identity_path = outdir / hashed_filename
                if not identity_path.exists():
                    identity_path.write_bytes(content)
                variants: dict[str, FileVariant] = {
                    "identity": FileVariant(
                        path_str=str(identity_path),
                        encoding="identity",
                        size=len(content),
                    )
                }
            else:
                # Use original file as identity
                variants = {
                    "identity": FileVariant(
                        path_str=str(file_path),
                        encoding="identity",
                        size=len(content),
                    )
                }

            # Compress if extension is compressible
            file_got_variant = False
            if ext.lower() in compressible_extensions:
                for encoding in encodings:
                    suffix = _ENCODING_SUFFIXES[encoding]

                    # Determine compressed file path
                    if outdir is not None:
                        compressed_path = outdir / f"{hashed_filename}{suffix}"
                    else:
                        compressed_path = file_path.with_suffix(ext + suffix)

                    # Skip compression if file already exists
                    if compressed_path.exists():
                        size = compressed_path.stat().st_size
                        if size < len(content):
                            variants[encoding] = FileVariant(
                                path_str=str(compressed_path),
                                encoding=encoding,
                                size=size,
                            )
                            stats.variants_reused += 1
                            stats.compressed_bytes += size
                            file_got_variant = True
                        else:
                            stats.variants_skipped += 1
                        continue

                    compressed = _compress_file(content, encoding)
                    # Only store if smaller than original
                    if len(compressed) < len(content):
                        compressed_path.write_bytes(compressed)
                        variants[encoding] = FileVariant(
                            path_str=str(compressed_path),
                            encoding=encoding,
                            size=len(compressed),
                        )
                        stats.variants_created += 1
                        stats.compressed_bytes += len(compressed)
                        file_got_variant = True
                    else:
                        stats.variants_skipped += 1

            if file_got_variant:
                stats.files_compressed += 1

            # Get content type
            content_type = _get_content_type(file_path)

            # Create entry
            entry = FileEntry(
                content_type=content_type,
                content_hash=content_hash,
                variants=variants,
                url=url,
                path_stem=path_stem,
            )

            path_to_url[rel_path_str] = url
            hash_to_entry[content_hash] = entry
            path_to_entry[rel_path_str] = entry

    return path_to_url, hash_to_entry, path_to_entry, stats


def prepare(
    directory: Path,
    *,
    outdir: Path | None = None,
    encodings: Iterable[Encoding] = ("zstd", "br", "gzip"),
    compressible_extensions: Iterable[str] = DEFAULT_COMPRESSIBLE_EXTENSIONS,
) -> dict[str, str]:
    """Pre-compress static files and return path-to-URL mapping.

    Use this to bake compressed files into Docker images at build time,
    or to prepare files for CDN upload.

    Args:
        directory: Path to the source static files directory
        outdir: Optional output directory for CAS files. If provided, hashed
            files and compressed variants are written here, keeping source
            files clean. If None, files are written alongside originals.
        encodings: Compression encodings to create, in priority order.
            Default: ("zstd", "br", "gzip")
        compressible_extensions: File extensions to compress.
            Default: DEFAULT_COMPRESSIBLE_EXTENSIONS

    Returns:
        Mapping of relative file paths to their hashed URLs.
        e.g., {"styles.css": "/styles.a1b2c3d4.css"}

    Example:
        # In Dockerfile or build script:
        from pathlib import Path
        from muxy.apps.static_files import prepare

        # Separate source and output directories
        manifest = prepare(Path("./static/src"), outdir=Path("./static/dist"))
        # Source files unchanged, CAS files in ./static/dist/
        # {"styles.css": "/styles.a1b2c3d4.css", ...}
    """
    encodings_tuple = tuple(encodings)
    compressible_set = frozenset(compressible_extensions)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    start_time = time.perf_counter()
    path_to_url, _, _, stats = _build_file_entries(
        directory, encodings_tuple, compressible_set, outdir
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "static_files.prepare: %d files (%d compressed), "
        "%d variants created, %d reused, %d skipped, %.1fms",
        stats.files_total,
        stats.files_compressed,
        stats.variants_created,
        stats.variants_reused,
        stats.variants_skipped,
        elapsed_ms,
    )

    return path_to_url


def _parse_hashed_path(path: str) -> tuple[str, str, str] | None:
    """Parse a hashed URL path like '/styles.a1b2c3d4.css'.

    Returns (directory, hash, extension) or None if invalid format.
    The directory includes the filename base (e.g., 'css/styles' from '/css/styles.a1b2c3d4.css').
    """
    # Remove leading slash
    if path.startswith("/"):
        path = path[1:]

    # Find the extension (last dot-separated segment)
    last_dot = path.rfind(".")
    if last_dot == -1:
        return None

    ext = path[last_dot:]  # e.g., ".css"
    base = path[:last_dot]  # e.g., "css/styles.a1b2c3d4"

    # Find the hash (last dot-separated segment of base)
    hash_dot = base.rfind(".")
    if hash_dot == -1:
        return None

    content_hash = base[hash_dot + 1 :]  # e.g., "a1b2c3d4"
    name_base = base[:hash_dot]  # e.g., "css/styles"

    # Validate hash is 8 hex characters
    if len(content_hash) != 8:
        return None
    try:
        int(content_hash, 16)
    except ValueError:
        return None

    return (name_base, content_hash, ext)


def static_files(
    directory: Path,
    *,
    outdir: Path | None = None,
    prefix: str | None = None,
    encodings: Iterable[Encoding] = ("zstd", "br", "gzip"),
    compressible_extensions: Iterable[str] = DEFAULT_COMPRESSIBLE_EXTENSIONS,
    canonical_redirect: bool = True,
) -> tuple[RSGIHTTPHandler, UrlPathFn]:
    """Create a compressed static files app using content-addressable storage.

    Files are pre-compressed at startup and served via hash-based URLs for
    optimal caching. URLs include a content hash for cache-busting:
    e.g., `/styles.a1b2c3d4.css`

    Args:
        directory: Path to the source static files directory
        outdir: Optional output directory for CAS files. If provided, hashed
            files and compressed variants are written here, keeping source
            files clean. If None, files are written alongside originals.
        prefix: URL prefix for mounting. Controls path extraction strategy:
            - None (default): Uses muxy's path_params from {path...} capture.
              Requires muxy and mounting with a catchall route.
            - str (e.g., "", "/static"): Uses prefix stripping on scope.path.
              Pure RSGI mode, works with any framework. Use "" for root mounting.
            The prefix is always prepended to url_path() results.
        encodings: Compression encodings to use, in priority order.
            Default: ("zstd", "br", "gzip")
        compressible_extensions: File extensions to compress.
            Default: DEFAULT_COMPRESSIBLE_EXTENSIONS
        canonical_redirect: When True (default), non-hashed paths redirect to
            their canonical hashed URLs. When False, non-hashed paths are served
            directly with no-cache headers. Set to False for source maps or
            other files where clients don't follow redirects.

    Returns:
        (app, url_path) tuple where:
        - app: RSGI HTTP handler for serving static files
        - url_path: Function to get content-addressed URL for a file path

    Example:
        from pathlib import Path
        from muxy import Router
        from muxy.apps.static_files import static_files

        # With separate source and output directories
        static_app, static_url = static_files(
            Path("./static/src"),
            outdir=Path("./static/dist"),
            prefix="/static",
        )
        router = Router()
        router.get("/static/{path...}", static_app)

        # In templates:
        # <link href="{{ static_url('styles.css') }}" rel="stylesheet">
        # -> <link href="/static/styles.a1b2c3d4.css" rel="stylesheet">
    """
    # Normalize inputs
    encodings_tuple = tuple(encodings)
    compressible_set = frozenset(compressible_extensions)

    # Normalize prefix (ensure no trailing slash if set)
    if prefix is not None:
        prefix = prefix.rstrip("/")

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)

    # Build server priority map (lower = higher priority)
    server_priority = {enc: i for i, enc in enumerate(encodings_tuple)}

    # Pre-compress files and build mappings at startup
    start_time = time.perf_counter()
    path_to_url, hash_to_entry, path_to_entry, stats = _build_file_entries(
        directory, encodings_tuple, compressible_set, outdir
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "static_files: %d files (%d compressed), "
        "%d variants created, %d reused, %d skipped, %.1fms",
        stats.files_total,
        stats.files_compressed,
        stats.variants_created,
        stats.variants_reused,
        stats.variants_skipped,
        elapsed_ms,
    )

    # Decide path extraction strategy at creation time:
    # - prefix=None: use muxy's path_params (requires {path...} route)
    # - prefix=str: use prefix stripping (pure RSGI, works anywhere)
    _use_path_params = prefix is None
    if _use_path_params:
        try:
            from muxy import path_params as _path_params
        except ImportError:
            msg = (
                "muxy is required when prefix is None. "
                "Set prefix (e.g., prefix='') for pure RSGI mode."
            )
            raise ImportError(msg) from None
    else:
        _path_params = None

    # Precompute prefix for url_path (empty string if None for muxy mode)
    _url_prefix = prefix if prefix is not None else ""

    def url_path(path: str) -> str | None:
        """Get content-addressable URL for a static file.

        Args:
            path: Relative path within the static directory (e.g., "styles.css")

        Returns:
            URL path with hash (e.g., "/static/styles.a1b2c3d4.css") or None if not found
        """
        # Single dict lookup, URL precomputed at startup
        url = path_to_url.get(path)
        if url is None:
            return None
        return _url_prefix + url

    async def app(scope: HTTPScope, proto: HTTPProtocol) -> None:
        """RSGI handler for serving static files."""
        # Path extraction strategy decided at creation time
        if _use_path_params:
            # muxy mode: get path from {path...} capture
            raw_path = "/" + _path_params.get()["path"]  # ty: ignore[possibly-missing-attribute]  # guaranteed not None in muxy mode
        else:
            # Pure RSGI mode: strip prefix from scope.path
            assert prefix is not None  # guaranteed by not _use_path_params
            raw_path = scope.path
            if prefix and raw_path.startswith(prefix):
                raw_path = raw_path[len(prefix) :]

        # Try hashed path first (content-addressable with long cache)
        entry: FileEntry | None = None

        parsed = _parse_hashed_path(raw_path)
        if parsed is not None:
            name_base, content_hash, _ext = parsed
            entry = hash_to_entry.get(content_hash)
            # Verify the path matches (precomputed string comparison)
            if entry is None or name_base != entry.path_stem:
                entry = None

        # Fall back to original path lookup
        if entry is None:
            lookup_path = raw_path[1:]  # Strip leading slash
            entry = path_to_entry.get(lookup_path)
            if entry is not None:
                if canonical_redirect:
                    # Redirect to canonical hashed URL (302 not cached)
                    # Derive prefix from actual request path (handles muxy mode)
                    request_prefix = scope.path[: -len(raw_path)] if raw_path else ""
                    redirect_url = request_prefix + entry.url
                    proto.response_empty(
                        302,
                        [("location", redirect_url), ("cache-control", "no-cache")],
                    )
                    return
                else:
                    # Serve directly with no-cache (for source maps, etc.)
                    variant = entry.variants["identity"]
                    proto.response_file(
                        200,
                        [
                            ("content-type", entry.content_type),
                            ("content-length", str(variant.size)),
                            ("cache-control", "public, max-age=0, must-revalidate"),
                        ],
                        variant.path_str,
                    )
                    return

        if entry is None:
            proto.response_bytes(404, [("content-type", "text/plain")], b"Not found")
            return

        # Content negotiation - select best encoding
        accept_encoding = scope.headers.get("accept-encoding")
        selected_encoding = _select_encoding(
            accept_encoding, server_priority, entry.variants.keys()
        )

        # Get the variant (fall back to identity if selected not available)
        variant = entry.variants.get(selected_encoding)
        if variant is None:
            variant = entry.variants["identity"]
            selected_encoding = "identity"

        # Build response headers with immutable cache (hashed URLs only)
        headers: list[tuple[str, str]] = [
            ("content-type", entry.content_type),
            ("content-length", str(variant.size)),
            ("cache-control", "public, max-age=31536000, immutable"),
            ("vary", "accept-encoding"),
        ]

        # Add content-encoding if not identity
        if selected_encoding != "identity":
            headers.append(("content-encoding", selected_encoding))

        # Send file response (path_str precomputed at startup)
        proto.response_file(200, headers, variant.path_str)

    return app, url_path
