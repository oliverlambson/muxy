"""Compression middleware with Zstd, Brotli, and Gzip support.

Compression priority: zstd > br > gzip (based on Accept-Encoding header).

Install with: uv add "muxy[compress]"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast, overload

if TYPE_CHECKING:
    from collections.abc import Buffer, Callable
    from typing import Literal

    from muxy.rsgi import (
        HTTPProtocol,
        HTTPScope,
        HTTPStreamTransport,
        RSGIHandler,
        RSGIHTTPHandler,
        RSGIWebsocketHandler,
        WebsocketProtocol,
        WebsocketScope,
    )

try:
    from cramjam import (
        brotli,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
        gzip,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
        zstd,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    )
except ImportError as e:
    msg = (
        "Compression middleware requires the 'compress' extra. "
        "Install with: uv add 'muxy[compress]'"
    )
    raise ImportError(msg) from e


class _StreamingCompressor(Protocol):
    """Protocol for cramjam streaming compressors."""

    def compress(self, data: bytes) -> None: ...
    def flush(self) -> Buffer: ...
    def finish(self) -> Buffer: ...


type EncodingName = Literal["zstd", "br", "gzip"]
type CompressionType = Literal["block", "streaming"]

type ZstdCompressionLevel = Literal[
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22
]
type BrotliCompressionLevel = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
type GzipCompressionLevel = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

type Zstd = tuple[
    Literal["zstd"],
    ZstdCompressionLevel | dict[CompressionType, ZstdCompressionLevel],
]
type Brotli = tuple[
    Literal["br"],
    BrotliCompressionLevel | dict[CompressionType, BrotliCompressionLevel],
]
type Gzip = tuple[
    Literal["gzip"],
    GzipCompressionLevel | dict[CompressionType, GzipCompressionLevel],
]

type EncodingOption = Zstd | Brotli | Gzip


_COMPRESSOR_MODULES = {"zstd": zstd, "br": brotli, "gzip": gzip}


def _get_compressor(name: EncodingName, config: EncodingOption) -> Compressor:
    name, levels = config
    level = _get_compression_level("block", levels)
    compressor = _COMPRESSOR_MODULES[name]
    return lambda data: bytes(compressor.compress(data, level=level))


def _get_streaming_compressor_factory(
    name: EncodingName, config: EncodingOption
) -> StreamingCompressorFactory:
    name, levels = config
    level = _get_compression_level("streaming", levels)
    compressor = _COMPRESSOR_MODULES[name]
    return lambda: compressor.Compressor(level=level)


def _get_compression_level[T: int](
    compression_type: CompressionType, levels: T | dict[CompressionType, T]
) -> T:
    if isinstance(levels, dict):
        return levels[compression_type]
    return levels


# Default compressible MIME types
DEFAULT_COMPRESSIBLE_TYPES: frozenset[str] = frozenset(
    {
        "text/html",
        "text/css",
        "text/plain",
        "text/javascript",
        "text/xml",
        "application/json",
        "application/javascript",
        "application/xml",
        "application/xhtml+xml",
        "image/svg+xml",
    }
)

# Minimum response size to compress (bytes)
DEFAULT_MIN_SIZE: int = 500


_DEFAULT_ZSTD_ENCODING: dict[CompressionType, ZstdCompressionLevel] = {
    "streaming": 3,
    "block": 3,
}
_DEFAULT_BROTLI_ENCODING: dict[CompressionType, BrotliCompressionLevel] = {
    "streaming": 4,
    "block": 6,
}
_DEFAULT_GZIP_ENCODING: dict[CompressionType, GzipCompressionLevel] = {
    "streaming": 6,
    "block": 6,
}
# Default encodings with priority (first = highest)
DEFAULT_ENCODINGS: tuple[EncodingOption, ...] = (
    ("zstd", _DEFAULT_ZSTD_ENCODING),
    ("br", _DEFAULT_BROTLI_ENCODING),
    ("gzip", _DEFAULT_GZIP_ENCODING),
)


type Compressor = Callable[[bytes], bytes]
type StreamingCompressorFactory = Callable[[], _StreamingCompressor]


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


type _EncodingData = tuple[Compressor, StreamingCompressorFactory]


def _build_encoding_cache(
    encodings: tuple[EncodingOption, ...],
) -> tuple[dict[str, int], dict[str, _EncodingData]]:
    """Pre-compute encoding priorities and compressors from config.

    Called once at middleware creation, not per-request.
    """
    priorities = {encodings[i][0]: i for i in range(len(encodings))}
    compressors = {
        encoding[0]: (
            _get_compressor(encoding[0], encoding),
            _get_streaming_compressor_factory(encoding[0], encoding),
        )
        for encoding in encodings
    }
    return priorities, compressors


def _select_encoding(
    accept_encoding: str,
    server_priority: dict[str, int],
    compressor_cache: dict[str, _EncodingData],
) -> tuple[str, Compressor, StreamingCompressorFactory] | None:
    """Select best available encoding based on Accept-Encoding header.

    When client qualities are equal, uses server priority order.
    Handles wildcard (*) which matches any encoding not explicitly listed.
    """
    client_encodings = _parse_accept_encoding(accept_encoding)

    supported: list[tuple[str, float]]
    if "*" not in accept_encoding:
        supported = [
            (name, quality)
            for name, quality in client_encodings
            if quality > 0 and name in server_priority
        ]
    else:
        wildcard_quality = 0.0
        explicit: dict[str, float] = {}
        for name, quality in client_encodings:
            if name == "*":
                wildcard_quality = quality
            else:
                explicit[name] = quality

        supported = []
        for name in server_priority:
            if name in explicit:
                quality = explicit[name]
            elif wildcard_quality > 0:
                quality = wildcard_quality
            else:
                continue
            if quality > 0:
                supported.append((name, quality))

    if not supported:
        return None

    # sort by quality descending, then by server preference ascending
    supported.sort(key=lambda x: (-x[1], server_priority[x[0]]))

    best_name = supported[0][0]
    compressor, streaming_factory = compressor_cache[best_name]
    return (best_name, compressor, streaming_factory)


class _CompressingHTTPStreamTransport:
    """Wraps HTTPStreamTransport to compress streamed data."""

    __slots__ = ("_compressor", "_finished", "_transport")

    def __init__(
        self,
        transport: HTTPStreamTransport,
        compressor: _StreamingCompressor,
    ) -> None:
        self._transport = transport
        self._compressor = compressor
        self._finished = False

    async def send_bytes(self, data: bytes) -> None:
        """Compress and send bytes."""
        self._compressor.compress(data)
        compressed = bytes(self._compressor.flush())
        if compressed:
            await self._transport.send_bytes(compressed)

    async def send_str(self, data: str) -> None:
        """Compress and send string."""
        await self.send_bytes(data.encode("utf-8"))

    async def _finish(self) -> None:
        """Finalize compression and send remaining bytes."""
        if self._finished:
            return
        self._finished = True
        final = bytes(self._compressor.finish())
        if final:
            try:
                await self._transport.send_bytes(final)
            except Exception:  # noqa: BLE001, S110
                pass  # usually because stream already closed


def _should_compress(
    headers: list[tuple[str, str]],
    body_size: int,
    compressible_types: frozenset[str],
    min_size: int,
) -> bool:
    """Determine if response should be compressed."""
    if body_size < min_size:  # don't compress small responses
        return False

    # extract content-type and check for existing compression
    content_type: str | None = None
    for name, value in headers:
        if name == "content-encoding":  # note RSGI guarantees header names lowercase
            return False  # don't double-compress
        if name == "content-type":
            # extract mime type without charset
            content_type = value.split(";", 1)[0].strip().lower()

    # only compress known compressible types
    return content_type is not None and content_type in compressible_types


class _CompressingHTTPProtocol:
    """Wraps HTTPProtocol to compress responses."""

    __slots__ = (
        "_compress",
        "_compressible_types",
        "_encoding",
        "_min_size",
        "_proto",
        "_stream",
        "_streaming_factory",
    )

    def __init__(
        self,
        proto: HTTPProtocol,
        encoding: str,
        compress: Compressor,
        streaming_factory: StreamingCompressorFactory,
        compressible_types: frozenset[str],
        min_size: int,
    ) -> None:
        self._proto = proto
        self._encoding = encoding
        self._compress = compress
        self._streaming_factory = streaming_factory
        self._compressible_types = compressible_types
        self._min_size = min_size
        self._stream: _CompressingHTTPStreamTransport | None = None

    async def __call__(self) -> bytes:
        """Read whole body."""
        return await self._proto()  # passthrough

    def __aiter__(self) -> bytes:
        """Read body chunks."""
        return self._proto.__aiter__()  # passthrough

    async def client_disconnect(self) -> None:
        """Watch for client disconnection."""
        await self._proto.client_disconnect()  # passthrough

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Send empty response."""
        self._proto.response_empty(status, headers)  # passthrough

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        """Send string response, compressing if appropriate."""
        body_bytes = body.encode("utf-8")
        self._send_compressed(status, headers, body_bytes)

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        """Send bytes response, compressing if appropriate."""
        self._send_compressed(status, headers, body)

    def _send_compressed(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        """Compress and send response if appropriate."""
        if _should_compress(
            headers, len(body), self._compressible_types, self._min_size
        ):
            compressed = self._compress(body)
            # Only use compressed version if it's actually smaller
            if len(compressed) < len(body):
                new_headers = [
                    (name, value) for name, value in headers if name != "content-length"
                ]
                new_headers.extend(
                    [
                        ("content-encoding", self._encoding),
                        ("vary", "accept-encoding"),
                        ("content-length", str(len(compressed))),
                    ]
                )
                self._proto.response_bytes(status, new_headers, compressed)
                return

        self._proto.response_bytes(status, headers, body)

    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None:
        """Send file response."""
        # passthrough
        # 1. Compressed static file serving is not handled here, that should be
        #    implemented elsewhere (e.g., as it's own dedicated RSGI handler).
        # 2. We could support dynamically compressing files here, but the point
        #    of RSGI's response file is to minimise overhead so it seems against
        #    the spirit of the method.
        self._proto.response_file(status, headers, file)

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        """Send file range response."""
        # passthrough
        # 1. Compressed static file serving is not handled here, that should be
        #    implemented elsewhere.
        # 2. We could support dynamically compressing files here, but the point
        #    of RSGI's response file is to minimise overhead so it seems against
        #    the spirit of the method.
        self._proto.response_file_range(status, headers, file, start, end)

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> _CompressingHTTPStreamTransport:
        """Start a compressed stream response."""
        # Build new headers, filtering out content-length/encoding and adding ours
        new_headers = [
            (name, value)
            for name, value in headers
            if name not in ("content-length", "content-encoding")
        ]
        new_headers.extend(
            [
                ("content-encoding", self._encoding),
                ("vary", "accept-encoding"),
            ]
        )

        transport = self._proto.response_stream(status, new_headers)
        compressor = self._streaming_factory()
        self._stream = _CompressingHTTPStreamTransport(transport, compressor)
        return self._stream

    async def _finalize(self) -> None:
        """Finalize any open stream. Called by middleware after inner handler returns."""
        if self._stream is not None:
            await self._stream._finish()


def compress(
    *,
    compressible_types: frozenset[str] = DEFAULT_COMPRESSIBLE_TYPES,
    min_size: int = DEFAULT_MIN_SIZE,
    encodings: tuple[EncodingOption, ...] = DEFAULT_ENCODINGS,
) -> Callable[[RSGIHandler], RSGIHandler]:
    """Create compression middleware.

    - Compresses relevant HTTP responses of wrapped handler, including streaming responses.
    - Uses Accept-Encoding header negotiation to select compression algorithm:
        - "Accept-Encoding: gzip, zstd, br" -> compress middleware uses zstd
        - "Accept-Encoding: br;q=1.0, gzip;q=0.8, *;q=0.1" -> compress middleware uses brotli

    Args:
        compressible_types: MIME types to compress
        min_size: Minimum response size in bytes to compress
        encodings: Tuple of (encoding_name, level) configurations in priority order.
            First encoding has highest priority when client accepts multiple.
            Level can be an int (same for block and streaming) or a dict with
            "block" and "streaming" keys for different levels.
            Default: zstd > br > gzip

    Returns:
        Middleware function that wraps handlers with compression

    Example:
        # Default: zstd > br > gzip
        router.use(compress())  #

        # Prefer brotli with high compression
        router.use(compress(encodings=(("br", 11), ("gzip", 9))))

        # Different levels for block vs streaming
        router.use(compress(encodings=(
            ("zstd", {"block": 9, "streaming": 3}),
        )))
    """
    # Pre-compute encoding data once at middleware creation
    priorities, compressors = _build_encoding_cache(encodings)

    def middleware(handler: RSGIHandler) -> RSGIHandler:
        @overload
        async def compressed_handler(scope: HTTPScope, proto: HTTPProtocol) -> None: ...
        @overload
        async def compressed_handler(
            scope: WebsocketScope, proto: WebsocketProtocol
        ) -> None: ...
        async def compressed_handler(
            scope: WebsocketScope | HTTPScope, proto: HTTPProtocol | WebsocketProtocol
        ) -> None:
            nonlocal handler

            if scope.proto != "http":  # passthrough websocket
                handler = cast("RSGIWebsocketHandler", handler)
                scope = cast("WebsocketScope", scope)
                proto = cast("WebsocketProtocol", proto)

                await handler(scope, proto)
                return

            handler = cast("RSGIHTTPHandler", handler)
            scope = cast("HTTPScope", scope)
            proto = cast("HTTPProtocol", proto)

            accept_encoding = scope.headers.get("accept-encoding")
            if accept_encoding is None:
                await handler(scope, proto)
                return

            selected = _select_encoding(accept_encoding, priorities, compressors)
            if selected is None:
                await handler(scope, proto)
                return

            encoding, compressor, streaming_factory = selected
            wrapped_proto = _CompressingHTTPProtocol(
                proto,
                encoding,
                compressor,
                streaming_factory,
                compressible_types,
                min_size,
            )
            await handler(scope, wrapped_proto)
            await wrapped_proto._finalize()

        return compressed_handler

    return middleware
