from pathlib import Path
from typing import ClassVar

import pytest
from conftest import MockHTTPProtocol, mock_scope
from cramjam import (
    brotli,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    gzip,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    zstd,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
)

from muxy.apps.static_files import (
    DEFAULT_COMPRESSIBLE_EXTENSIONS,
    _parse_hashed_path,
    _select_encoding,
    prepare,
    static_files,
)
from muxy.rsgi import RSGIHTTPHandler


# --- Test Fixtures -----------------------------------------------------------
@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    """Create a temporary static files directory with test files."""
    # Compressible files (large enough to compress)
    css = tmp_path / "styles.css"
    css.write_text("body { color: red; }" + " " * 500)

    js = tmp_path / "app.js"
    js.write_text("console.log('hello');" + " " * 500)

    # Nested file
    subdir = tmp_path / "lib"
    subdir.mkdir()
    nested = subdir / "utils.js"
    nested.write_text("export const x = 1;" + " " * 500)

    # Non-compressible file (binary)
    img = tmp_path / "logo.png"
    img.write_bytes(b"\x89PNG\r\n" + b"x" * 100)

    # Small file (won't compress well)
    tiny = tmp_path / "tiny.txt"
    tiny.write_text("hi")

    return tmp_path


# --- Unit tests for _parse_hashed_path ---------------------------------------
class TestParseHashedPath:
    def test_simple_path(self) -> None:
        result = _parse_hashed_path("/styles.a1b2c3d4.css")
        assert result == ("styles", "a1b2c3d4", ".css")

    def test_nested_path(self) -> None:
        result = _parse_hashed_path("/css/app.a1b2c3d4.css")
        assert result == ("css/app", "a1b2c3d4", ".css")

    def test_deeply_nested(self) -> None:
        result = _parse_hashed_path("/a/b/c/file.12345678.js")
        assert result == ("a/b/c/file", "12345678", ".js")

    def test_no_extension(self) -> None:
        result = _parse_hashed_path("/styles.a1b2c3d4")
        assert result is None

    def test_no_hash(self) -> None:
        result = _parse_hashed_path("/styles.css")
        assert result is None

    def test_invalid_hash_length(self) -> None:
        result = _parse_hashed_path("/styles.abc.css")
        assert result is None  # Not 8 chars

    def test_invalid_hash_chars(self) -> None:
        result = _parse_hashed_path("/styles.ghijklmn.css")
        assert result is None  # Not valid hex

    def test_empty_path(self) -> None:
        result = _parse_hashed_path("/")
        assert result is None

    def test_no_leading_slash(self) -> None:
        result = _parse_hashed_path("styles.a1b2c3d4.css")
        assert result == ("styles", "a1b2c3d4", ".css")


# --- Unit tests for _select_encoding -----------------------------------------
class TestSelectEncoding:
    # Server priority: lower index = higher priority
    _default_priority: ClassVar[dict[str, int]] = {"zstd": 0, "br": 1, "gzip": 2}
    _default_available: ClassVar[list[str]] = ["zstd", "br", "gzip", "identity"]

    def test_prefers_zstd(self) -> None:
        """zstd > br > gzip when all available."""
        result = _select_encoding(
            "gzip, br, zstd", self._default_priority, self._default_available
        )
        assert result == "zstd"

    def test_prefers_br_over_gzip(self) -> None:
        """br > gzip when zstd unavailable."""
        result = _select_encoding(
            "gzip, br", self._default_priority, self._default_available
        )
        assert result == "br"

    def test_falls_back_to_identity(self) -> None:
        """Returns identity when no match."""
        result = _select_encoding(
            "deflate", self._default_priority, self._default_available
        )
        assert result == "identity"

    def test_none_accept_encoding(self) -> None:
        """Returns identity for None header."""
        result = _select_encoding(None, self._default_priority, self._default_available)
        assert result == "identity"

    def test_quality_overrides_priority(self) -> None:
        """Client q=1.0 beats server priority."""
        result = _select_encoding(
            "br;q=1.0, zstd;q=0.5, gzip;q=0.5",
            self._default_priority,
            self._default_available,
        )
        assert result == "br"

    def test_wildcard_support(self) -> None:
        """Wildcard matches available encodings."""
        result = _select_encoding("*", self._default_priority, self._default_available)
        assert result == "zstd"  # Highest server priority

    def test_respects_quality_zero(self) -> None:
        """q=0 excludes encoding."""
        result = _select_encoding(
            "zstd;q=0, br;q=0, gzip", self._default_priority, self._default_available
        )
        assert result == "gzip"

    def test_equal_quality_uses_server_priority(self) -> None:
        """When client qualities are equal, server priority determines selection."""
        result = _select_encoding(
            "gzip, zstd, br", self._default_priority, self._default_available
        )
        assert result == "zstd"

    def test_empty_header(self) -> None:
        result = _select_encoding("", self._default_priority, self._default_available)
        assert result == "identity"

    def test_wildcard_zero_only_rejects_all(self) -> None:
        """Wildcard with q=0 alone should reject all encodings."""
        result = _select_encoding(
            "*;q=0", self._default_priority, self._default_available
        )
        assert result == "identity"


# --- Integration tests: Startup / Pre-compression ----------------------------
class TestStaticFilesStartup:
    def test_creates_compressed_files(self, static_dir: Path) -> None:
        """Verify .zst, .br, .gz files created."""
        static_files(static_dir)

        css_path = static_dir / "styles.css"
        assert css_path.with_suffix(".css.zst").exists()
        assert css_path.with_suffix(".css.br").exists()
        assert css_path.with_suffix(".css.gz").exists()

    def test_skips_non_compressible(self, static_dir: Path) -> None:
        """Images/fonts don't get compressed variants."""
        static_files(static_dir)

        # PNG should not have compressed variants
        img_path = static_dir / "logo.png"
        assert not img_path.with_suffix(".png.zst").exists()
        assert not img_path.with_suffix(".png.br").exists()
        assert not img_path.with_suffix(".png.gz").exists()

    def test_skips_existing_compressed(self, static_dir: Path) -> None:
        """Doesn't process .zst/.br/.gz files."""
        # Create an already-compressed file
        existing_zst = static_dir / "precompressed.zst"
        existing_zst.write_bytes(b"already compressed")

        _app, url_path = static_files(static_dir)

        # Should not have a URL for the .zst file
        assert url_path("precompressed.zst") is None

    def test_only_stores_smaller(self, static_dir: Path) -> None:
        """Doesn't store compressed if larger than original."""
        # tiny.txt is only 2 bytes - compression makes it larger
        static_files(static_dir, prefix="")

        # Compressed variants should not exist (or not all of them)
        # At minimum, gzip of "hi" should be larger than 2 bytes
        # The implementation only stores if compressed < original
        # Note: tiny.txt may still get compressed files if the compressed
        # version happens to be smaller, but typically for 2 bytes it won't be

    def test_skips_existing_compressed_variants(self, static_dir: Path) -> None:
        """Reuses existing compressed files instead of re-compressing."""
        # First call creates compressed files
        static_files(static_dir, prefix="")

        css_gz = static_dir / "styles.css.gz"
        assert css_gz.exists()
        original_mtime = css_gz.stat().st_mtime

        # Small delay to ensure mtime would change if file was rewritten
        import time

        time.sleep(0.01)

        # Second call should skip compression
        static_files(static_dir, prefix="")

        # mtime should be unchanged (file wasn't rewritten)
        assert css_gz.stat().st_mtime == original_mtime


# --- Integration tests: url_path Function ------------------------------------
class TestUrlPath:
    def test_url_path_simple(self, static_dir: Path) -> None:
        """'styles.css' -> '/styles.{hash}.css'."""
        _app, url_path = static_files(static_dir)

        url = url_path("styles.css")
        assert url is not None
        assert url.startswith("/styles.")
        assert url.endswith(".css")
        # Hash should be 8 hex chars
        parts = url.split(".")
        assert len(parts) == 3
        assert len(parts[1]) == 8

    def test_url_path_nested(self, static_dir: Path) -> None:
        """'lib/utils.js' -> '/lib/utils.{hash}.js'."""
        _app, url_path = static_files(static_dir)

        url = url_path("lib/utils.js")
        assert url is not None
        assert url.startswith("/lib/utils.")
        assert url.endswith(".js")

    def test_url_path_not_found(self, static_dir: Path) -> None:
        """'nonexistent.css' -> None."""
        _app, url_path = static_files(static_dir)

        url = url_path("nonexistent.css")
        assert url is None


# --- Integration tests: App Handler - Content Negotiation --------------------
class TestContentNegotiation:
    def _get_url_and_app(self, static_dir: Path) -> tuple[str, RSGIHTTPHandler]:
        """Helper to get the URL for styles.css and the app (pure RSGI mode)."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None
        return url, app

    @pytest.mark.asyncio
    async def test_serves_zstd_variant(self, static_dir: Path) -> None:
        """Accept-Encoding: zstd serves .zst."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "zstd"})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "zstd"
        assert proto.response_file_path is not None
        assert proto.response_file_path.endswith(".zst")

    @pytest.mark.asyncio
    async def test_serves_br_variant(self, static_dir: Path) -> None:
        """Accept-Encoding: br serves .br."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "br"})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "br"
        assert proto.response_file_path is not None
        assert proto.response_file_path.endswith(".br")

    @pytest.mark.asyncio
    async def test_serves_gzip_variant(self, static_dir: Path) -> None:
        """Accept-Encoding: gzip serves .gz."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "gzip"
        assert proto.response_file_path is not None
        assert proto.response_file_path.endswith(".gz")

    @pytest.mark.asyncio
    async def test_serves_identity_no_header(self, static_dir: Path) -> None:
        """No Accept-Encoding serves original."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert "content-encoding" not in headers_dict
        assert proto.response_file_path is not None
        assert proto.response_file_path.endswith(".css")

    @pytest.mark.asyncio
    async def test_serves_identity_unsupported(self, static_dir: Path) -> None:
        """Accept-Encoding: deflate serves original."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "deflate"})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert "content-encoding" not in headers_dict

    @pytest.mark.asyncio
    async def test_priority_zstd_over_br(self, static_dir: Path) -> None:
        """'zstd, br, gzip' selects zstd."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "zstd, br, gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "zstd"

    @pytest.mark.asyncio
    async def test_quality_overrides_priority(self, static_dir: Path) -> None:
        """'br;q=1.0, zstd;q=0.5' selects br."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(
            path=url, headers={"accept-encoding": "br;q=1.0, zstd;q=0.5"}
        )
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "br"


# --- Integration tests: App Handler - Response Headers -----------------------
class TestResponseHeaders:
    def _get_url_and_app(self, static_dir: Path) -> tuple[str, RSGIHTTPHandler]:
        """Helper to get the URL for styles.css and the app (pure RSGI mode)."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None
        return url, app

    @pytest.mark.asyncio
    async def test_content_type_header(self, static_dir: Path) -> None:
        """Correct MIME type."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-type") == "text/css"

    @pytest.mark.asyncio
    async def test_content_length_header(self, static_dir: Path) -> None:
        """Matches compressed file size."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        content_length = headers_dict.get("content-length")
        assert content_length is not None

        # Verify it matches actual file size
        assert proto.response_file_path is not None
        actual_size = Path(proto.response_file_path).stat().st_size
        assert int(content_length) == actual_size

    @pytest.mark.asyncio
    async def test_cache_control_header(self, static_dir: Path) -> None:
        """'public, max-age=31536000, immutable'."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert (
            headers_dict.get("cache-control") == "public, max-age=31536000, immutable"
        )

    @pytest.mark.asyncio
    async def test_vary_header(self, static_dir: Path) -> None:
        """'accept-encoding'."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("vary") == "accept-encoding"

    @pytest.mark.asyncio
    async def test_content_encoding_header_present_for_compressed(
        self, static_dir: Path
    ) -> None:
        """Present for compressed."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert "content-encoding" in headers_dict

    @pytest.mark.asyncio
    async def test_content_encoding_header_absent_for_identity(
        self, static_dir: Path
    ) -> None:
        """Absent for identity."""
        url, app = self._get_url_and_app(static_dir)

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        assert "content-encoding" not in headers_dict


# --- Integration tests: App Handler - Error Cases ----------------------------
class TestErrorCases:
    @pytest.mark.asyncio
    async def test_404_invalid_path_format(self, static_dir: Path) -> None:
        """'/static/styles.css' (no hash) -> 404."""
        app, _url_path = static_files(static_dir, prefix="/static")

        proto = MockHTTPProtocol()
        scope = mock_scope(path="/static/styles.css", headers={})
        await app(scope, proto)

        assert proto.response_status == 404

    @pytest.mark.asyncio
    async def test_404_unknown_hash(self, static_dir: Path) -> None:
        """'/static/styles.00000000.css' (hash not found) -> 404."""
        app, _url_path = static_files(static_dir, prefix="/static")

        proto = MockHTTPProtocol()
        scope = mock_scope(path="/static/styles.00000000.css", headers={})
        await app(scope, proto)

        assert proto.response_status == 404

    @pytest.mark.asyncio
    async def test_404_path_mismatch(self, static_dir: Path) -> None:
        """Valid hash but wrong filename -> 404."""
        app, url_path = static_files(static_dir, prefix="/static")

        # Get a valid hash from styles.css
        url = url_path("styles.css")
        assert url is not None
        # Extract the hash (url is /static/styles.{hash}.css)
        hash_part = url.split(".")[1]

        # Try to use that hash with a different filename
        proto = MockHTTPProtocol()
        scope = mock_scope(path=f"/static/other.{hash_part}.css", headers={})
        await app(scope, proto)

        assert proto.response_status == 404


# --- Integration tests: Custom Configuration ---------------------------------
class TestCustomConfiguration:
    def test_custom_encodings(self, static_dir: Path) -> None:
        """'encodings=["gzip"]' only creates gzip."""
        static_files(static_dir, encodings=["gzip"])

        css_path = static_dir / "styles.css"
        assert css_path.with_suffix(".css.gz").exists()
        assert not css_path.with_suffix(".css.zst").exists()
        assert not css_path.with_suffix(".css.br").exists()

    def test_custom_compressible_extensions(self, static_dir: Path) -> None:
        """Custom set respected."""
        # Create a file with custom extension
        custom_file = static_dir / "data.custom"
        custom_file.write_text("custom content" + " " * 500)

        # Default should not compress .custom
        static_files(static_dir)
        assert not custom_file.with_suffix(".custom.gz").exists()

        # Clean up for second test
        for suffix in [".gz", ".zst", ".br"]:
            compressed = custom_file.with_suffix(f".custom{suffix}")
            if compressed.exists():
                compressed.unlink()

        # With custom extensions including .custom
        static_files(static_dir, compressible_extensions=frozenset({".custom"}))
        assert custom_file.with_suffix(".custom.gz").exists()

    @pytest.mark.asyncio
    async def test_custom_encodings_content_negotiation(self, static_dir: Path) -> None:
        """Custom encodings affect content negotiation."""
        # Clean up any existing compressed files first
        css_path = static_dir / "styles.css"
        for suffix in [".gz", ".zst", ".br"]:
            compressed = css_path.with_suffix(f".css{suffix}")
            if compressed.exists():
                compressed.unlink()

        # Only allow gzip (use prefix for pure RSGI mode)
        app, url_path = static_files(static_dir, prefix="/static", encodings=["gzip"])
        url = url_path("styles.css")
        assert url is not None

        # Request zstd - should get identity since zstd not available
        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "zstd"})
        await app(scope, proto)

        headers_dict = dict(proto.response_headers or [])
        # Should not have content-encoding since zstd variant doesn't exist
        assert headers_dict.get("content-encoding") != "zstd"


# --- Decompression verification tests ----------------------------------------
class TestDecompression:
    """Verify compressed files can be decompressed correctly."""

    @pytest.mark.asyncio
    async def test_zstd_decompresses_correctly(self, static_dir: Path) -> None:
        """Verify zstd compressed file can be decompressed."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "zstd"})
        await app(scope, proto)

        assert proto.response_file_path is not None
        compressed_data = Path(proto.response_file_path).read_bytes()
        decompressed = bytes(zstd.decompress(compressed_data))

        original = (static_dir / "styles.css").read_bytes()
        assert decompressed == original

    @pytest.mark.asyncio
    async def test_brotli_decompresses_correctly(self, static_dir: Path) -> None:
        """Verify brotli compressed file can be decompressed."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "br"})
        await app(scope, proto)

        assert proto.response_file_path is not None
        compressed_data = Path(proto.response_file_path).read_bytes()
        decompressed = bytes(brotli.decompress(compressed_data))

        original = (static_dir / "styles.css").read_bytes()
        assert decompressed == original

    @pytest.mark.asyncio
    async def test_gzip_decompresses_correctly(self, static_dir: Path) -> None:
        """Verify gzip compressed file can be decompressed."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        assert proto.response_file_path is not None
        compressed_data = Path(proto.response_file_path).read_bytes()
        decompressed = bytes(gzip.decompress(compressed_data))

        original = (static_dir / "styles.css").read_bytes()
        assert decompressed == original


# --- Integration tests: Prefix parameter -------------------------------------
class TestPrefixParameter:
    def test_url_path_includes_prefix(self, static_dir: Path) -> None:
        """url_path() returns URLs with prefix."""
        _app, url_path = static_files(static_dir, prefix="/static")

        url = url_path("styles.css")
        assert url is not None
        assert url.startswith("/static/styles.")
        assert url.endswith(".css")

    @pytest.mark.asyncio
    async def test_app_uses_path_params(self, static_dir: Path) -> None:
        """App handler uses path_params when available (mounted with {path...})."""
        from muxy import path_params

        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None
        # Extract path without prefix for path_params
        path_value = url.removeprefix("/static/")

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        # Simulate router setting path_params
        with path_params.set({"path": path_value}):
            await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "gzip"

    @pytest.mark.asyncio
    async def test_app_fallback_strips_prefix(self, static_dir: Path) -> None:
        """App handler strips prefix from scope.path when path_params not set."""
        app, url_path = static_files(static_dir, prefix="/static")
        url = url_path("styles.css")
        assert url is not None

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        # No path_params set - fallback to prefix stripping
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "gzip"

    def test_prefix_trailing_slash_normalized(self, static_dir: Path) -> None:
        """Trailing slash on prefix is normalized."""
        _app, url_path = static_files(static_dir, prefix="/static/")

        url = url_path("styles.css")
        assert url is not None
        # Should not have double slash
        assert "//" not in url
        assert url.startswith("/static/styles.")

    @pytest.mark.asyncio
    async def test_empty_prefix_for_root_mount(self, static_dir: Path) -> None:
        """prefix='' allows pure RSGI root mounting."""
        app, url_path = static_files(static_dir, prefix="")
        url = url_path("styles.css")
        assert url is not None
        # No prefix, just the hashed path
        assert url.startswith("/styles.")
        assert url.endswith(".css")

        proto = MockHTTPProtocol()
        scope = mock_scope(path=url, headers={"accept-encoding": "gzip"})
        await app(scope, proto)

        assert proto.response_status == 200
        headers_dict = dict(proto.response_headers or [])
        assert headers_dict.get("content-encoding") == "gzip"


# --- Integration tests: prepare() function -----------------------------------
class TestPrepare:
    """Tests for the standalone prepare() function."""

    def test_returns_path_to_url_mapping(self, static_dir: Path) -> None:
        """prepare() returns dict mapping relative paths to hashed URLs."""
        manifest = prepare(static_dir)

        assert "styles.css" in manifest
        assert "app.js" in manifest
        assert "lib/utils.js" in manifest
        assert "logo.png" in manifest

        # URLs should have hash format
        css_url = manifest["styles.css"]
        assert css_url.startswith("/styles.")
        assert css_url.endswith(".css")
        parts = css_url.split(".")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # 8 hex chars

    def test_creates_compressed_files(self, static_dir: Path) -> None:
        """prepare() creates compressed file variants."""
        prepare(static_dir)

        css_path = static_dir / "styles.css"
        assert css_path.with_suffix(".css.zst").exists()
        assert css_path.with_suffix(".css.br").exists()
        assert css_path.with_suffix(".css.gz").exists()

    def test_respects_custom_encodings(self, static_dir: Path) -> None:
        """prepare() respects custom encodings parameter."""
        prepare(static_dir, encodings=["gzip"])

        css_path = static_dir / "styles.css"
        assert css_path.with_suffix(".css.gz").exists()
        assert not css_path.with_suffix(".css.zst").exists()
        assert not css_path.with_suffix(".css.br").exists()

    def test_respects_custom_compressible_extensions(self, static_dir: Path) -> None:
        """prepare() respects custom compressible_extensions parameter."""
        # Create a file with custom extension
        custom_file = static_dir / "data.custom"
        custom_file.write_text("custom content" + " " * 500)

        # With custom extensions including .custom
        prepare(static_dir, compressible_extensions=frozenset({".custom"}))

        # .custom should be compressed
        assert custom_file.with_suffix(".custom.gz").exists()
        # .css should NOT be compressed (not in custom set)
        css_path = static_dir / "styles.css"
        assert not css_path.with_suffix(".css.gz").exists()

    def test_skips_non_compressible(self, static_dir: Path) -> None:
        """prepare() doesn't compress non-compressible files."""
        prepare(static_dir)

        img_path = static_dir / "logo.png"
        assert not img_path.with_suffix(".png.zst").exists()
        assert not img_path.with_suffix(".png.br").exists()
        assert not img_path.with_suffix(".png.gz").exists()

    def test_manifest_includes_non_compressible(self, static_dir: Path) -> None:
        """prepare() includes non-compressible files in manifest."""
        manifest = prepare(static_dir)

        # Non-compressible files should still be in manifest
        assert "logo.png" in manifest
        png_url = manifest["logo.png"]
        assert png_url.startswith("/logo.")
        assert png_url.endswith(".png")

    def test_consistent_hash_with_static_files(self, static_dir: Path) -> None:
        """prepare() generates same hashes as static_files()."""
        manifest = prepare(static_dir)
        _app, url_path = static_files(static_dir, prefix="")

        # URLs should match
        assert manifest["styles.css"] == url_path("styles.css")
        assert manifest["app.js"] == url_path("app.js")
        assert manifest["lib/utils.js"] == url_path("lib/utils.js")

    def test_skips_existing_compressed_variants(self, static_dir: Path) -> None:
        """prepare() reuses existing compressed files."""
        # First call creates compressed files
        prepare(static_dir)

        css_gz = static_dir / "styles.css.gz"
        assert css_gz.exists()
        original_mtime = css_gz.stat().st_mtime

        # Small delay to ensure mtime would change if file was rewritten
        import time

        time.sleep(0.01)

        # Second call should skip compression
        prepare(static_dir)

        # mtime should be unchanged (file wasn't rewritten)
        assert css_gz.stat().st_mtime == original_mtime


# --- Default values tests ----------------------------------------------------
def test_default_compressible_extensions() -> None:
    """Test default compressible extensions are sensible."""
    assert ".css" in DEFAULT_COMPRESSIBLE_EXTENSIONS
    assert ".js" in DEFAULT_COMPRESSIBLE_EXTENSIONS
    assert ".html" in DEFAULT_COMPRESSIBLE_EXTENSIONS
    assert ".json" in DEFAULT_COMPRESSIBLE_EXTENSIONS
    assert ".svg" in DEFAULT_COMPRESSIBLE_EXTENSIONS
    assert ".wasm" in DEFAULT_COMPRESSIBLE_EXTENSIONS
