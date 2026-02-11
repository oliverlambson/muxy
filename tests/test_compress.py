from typing import cast

import pytest
from conftest import MockHTTPProtocol, mock_scope
from cramjam import (
    brotli,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    gzip,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
    zstd,  # ty: ignore[unresolved-import]  # fixed in cramjam >2.11
)

from muxy.middleware.compress import (
    DEFAULT_COMPRESSIBLE_TYPES,
    DEFAULT_ENCODINGS,
    DEFAULT_MIN_SIZE,
    _build_encoding_cache,
    _parse_accept_encoding,
    _select_encoding,
    compress,
)
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler


# --- Unit tests for helper functions ------------------------------------------
class TestParseAcceptEncoding:
    def test_single_encoding(self) -> None:
        result = _parse_accept_encoding("gzip")
        assert result == [("gzip", 1.0)]

    def test_multiple_encodings(self) -> None:
        result = _parse_accept_encoding("gzip, br, zstd")
        assert result == [("gzip", 1.0), ("br", 1.0), ("zstd", 1.0)]

    def test_quality_values(self) -> None:
        result = _parse_accept_encoding("gzip;q=0.5, br;q=0.9, zstd;q=1.0")
        assert result == [("gzip", 0.5), ("br", 0.9), ("zstd", 1.0)]

    def test_mixed_quality(self) -> None:
        result = _parse_accept_encoding("gzip, br;q=0.8")
        assert result == [("gzip", 1.0), ("br", 0.8)]

    def test_empty_string(self) -> None:
        result = _parse_accept_encoding("")
        assert result == []

    def test_whitespace_handling(self) -> None:
        result = _parse_accept_encoding("  gzip  ,  br  ")
        assert result == [("gzip", 1.0), ("br", 1.0)]


class TestSelectEncoding:
    # Pre-compute cache once for default encodings
    _default_priority, _default_cache = _build_encoding_cache(DEFAULT_ENCODINGS)

    def test_prefers_zstd(self) -> None:
        result = _select_encoding(
            "gzip, br, zstd", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "zstd"

    def test_prefers_br_over_gzip(self) -> None:
        result = _select_encoding(
            "gzip, br", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "br"

    def test_falls_back_to_gzip(self) -> None:
        result = _select_encoding("gzip", self._default_priority, self._default_cache)
        assert result is not None
        assert result[0] == "gzip"

    def test_no_supported_encoding(self) -> None:
        result = _select_encoding(
            "deflate, identity", self._default_priority, self._default_cache
        )
        assert result is None

    def test_respects_quality_zero(self) -> None:
        result = _select_encoding(
            "zstd;q=0, br;q=0, gzip", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "gzip"

    def test_quality_overrides_server_priority(self) -> None:
        """When client specifies different qualities, higher quality wins over server priority."""
        # Server prefers zstd > br > gzip, but client prefers br (q=1.0) over others
        result = _select_encoding(
            "br;q=1.0, gzip;q=0.8, *;q=0.1", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "br"

    def test_equal_quality_uses_server_priority(self) -> None:
        """When client qualities are equal, server priority determines selection."""
        # All equal quality (1.0), server prefers zstd
        result = _select_encoding(
            "gzip, zstd, br", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "zstd"

    def test_empty_header(self) -> None:
        result = _select_encoding("", self._default_priority, self._default_cache)
        assert result is None

    def test_custom_priority(self) -> None:
        # Prefer brotli over zstd
        custom_encodings = (("br", 4), ("zstd", 3), ("gzip", 6))
        priority, cache = _build_encoding_cache(custom_encodings)
        result = _select_encoding("gzip, br, zstd", priority, cache)
        assert result is not None
        assert result[0] == "br"

    def test_limited_encodings(self) -> None:
        # Only allow gzip
        custom_encodings = (("gzip", 6),)
        priority, cache = _build_encoding_cache(custom_encodings)
        result = _select_encoding("gzip, br, zstd", priority, cache)
        assert result is not None
        assert result[0] == "gzip"

    def test_no_match_with_limited_encodings(self) -> None:
        # Only allow zstd, but client only accepts gzip
        custom_encodings = (("zstd", 3),)
        priority, cache = _build_encoding_cache(custom_encodings)
        result = _select_encoding("gzip", priority, cache)
        assert result is None

    def test_wildcard_matches_unlisted_encodings(self) -> None:
        """Wildcard (*) should match server encodings not explicitly listed by client."""
        # Client lists gzip but * matches zstd and br
        result = _select_encoding(
            "gzip;q=0.5, *;q=0.8", self._default_priority, self._default_cache
        )
        assert result is not None
        # zstd should win: quality 0.8 (from *) beats gzip's 0.5, and zstd has highest server priority
        assert result[0] == "zstd"

    def test_wildcard_lower_quality_than_explicit(self) -> None:
        """Explicit encoding quality should override wildcard for that encoding."""
        # br explicitly q=1.0, others get q=0.1 from wildcard
        result = _select_encoding(
            "br;q=1.0, gzip;q=0.8, *;q=0.1", self._default_priority, self._default_cache
        )
        assert result is not None
        # br wins with explicit q=1.0
        assert result[0] == "br"

    def test_wildcard_zero_rejects_unlisted(self) -> None:
        """Wildcard with q=0 should reject unlisted encodings."""
        # Only gzip explicitly allowed, * rejects everything else
        result = _select_encoding(
            "gzip, *;q=0", self._default_priority, self._default_cache
        )
        assert result is not None
        assert result[0] == "gzip"

    def test_wildcard_only(self) -> None:
        """Wildcard alone should match all server encodings."""
        result = _select_encoding("*", self._default_priority, self._default_cache)
        assert result is not None
        # Server priority determines: zstd wins
        assert result[0] == "zstd"

    def test_wildcard_zero_only_rejects_all(self) -> None:
        """Wildcard with q=0 alone should reject all encodings."""
        result = _select_encoding("*;q=0", self._default_priority, self._default_cache)
        assert result is None


# --- Integration tests for middleware -----------------------------------------
@pytest.mark.asyncio
async def test_compress_json_with_zstd() -> None:
    """Test compression of JSON response with zstd."""
    large_json = '{"data": "' + "x" * 1000 + '"}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(
            200,
            [("content-type", "application/json")],
            large_json,
        )

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "zstd, br, gzip"})
    await wrapped(scope, proto)

    assert proto.response_status == 200
    assert proto.response_body is not None
    assert len(proto.response_body) < len(large_json.encode())

    # Verify content-encoding header
    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "zstd"
    assert headers_dict.get("vary") == "accept-encoding"

    # Verify we can decompress
    decompressed = bytes(zstd.decompress(proto.response_body))
    assert decompressed.decode() == large_json


@pytest.mark.asyncio
async def test_compress_json_with_brotli() -> None:
    """Test compression with brotli when zstd not accepted."""
    large_json = '{"data": "' + "x" * 1000 + '"}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(
            200,
            [("content-type", "application/json")],
            large_json,
        )

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "br, gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "br"

    # Verify we can decompress
    assert proto.response_body is not None
    decompressed = bytes(brotli.decompress(proto.response_body))
    assert decompressed.decode() == large_json


@pytest.mark.asyncio
async def test_compress_json_with_gzip() -> None:
    """Test compression with gzip when only gzip accepted."""
    large_json = '{"data": "' + "x" * 1000 + '"}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(
            200,
            [("content-type", "application/json")],
            large_json,
        )

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "gzip"

    # Verify we can decompress
    assert proto.response_body is not None
    decompressed = bytes(gzip.decompress(proto.response_body))
    assert decompressed.decode() == large_json


@pytest.mark.asyncio
async def test_no_compression_without_accept_encoding() -> None:
    """Test no compression when client doesn't accept any encoding."""
    body = '{"data": "' + "x" * 1000 + '"}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [("content-type", "application/json")], body)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert "content-encoding" not in headers_dict
    assert proto.response_body == body.encode()


@pytest.mark.asyncio
async def test_no_compression_for_small_response() -> None:
    """Test no compression for responses smaller than min_size."""
    small_body = '{"ok": true}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [("content-type", "application/json")], small_body)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert "content-encoding" not in headers_dict


@pytest.mark.asyncio
async def test_no_compression_for_non_compressible_type() -> None:
    """Test no compression for non-compressible content types."""
    body = b"\x89PNG\r\n" + b"x" * 1000  # Fake PNG

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_bytes(200, [("content-type", "image/png")], body)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert "content-encoding" not in headers_dict
    assert proto.response_body == body


@pytest.mark.asyncio
async def test_no_double_compression() -> None:
    """Test already-compressed responses are not re-compressed."""
    body = b"already compressed data" * 50

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_bytes(
            200,
            [("content-type", "application/json"), ("content-encoding", "gzip")],
            body,
        )

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    # Should pass through unchanged
    assert proto.response_body == body
    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "gzip"


@pytest.mark.asyncio
async def test_custom_min_size() -> None:
    """Test custom min_size parameter."""
    body = "x" * 100  # 100 bytes

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [("content-type", "text/plain")], body)

    # Default min_size is 500, so this shouldn't compress
    middleware_default = compress()
    wrapped_default = cast(RSGIHTTPHandler, middleware_default(handler))

    proto1 = MockHTTPProtocol()
    scope1 = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped_default(scope1, proto1)

    headers_dict1 = dict(proto1.response_headers or [])
    assert "content-encoding" not in headers_dict1

    # With min_size=50, it should compress
    middleware_custom = compress(min_size=50)
    wrapped_custom = cast(RSGIHTTPHandler, middleware_custom(handler))

    proto2 = MockHTTPProtocol()
    scope2 = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped_custom(scope2, proto2)

    headers_dict2 = dict(proto2.response_headers or [])
    assert headers_dict2.get("content-encoding") == "gzip"


@pytest.mark.asyncio
async def test_custom_compressible_types() -> None:
    """Test custom compressible_types parameter."""
    body = "x" * 1000

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [("content-type", "application/x-custom")], body)

    # Default types don't include application/x-custom
    middleware_default = compress()
    wrapped_default = cast(RSGIHTTPHandler, middleware_default(handler))

    proto1 = MockHTTPProtocol()
    scope1 = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped_default(scope1, proto1)

    headers_dict1 = dict(proto1.response_headers or [])
    assert "content-encoding" not in headers_dict1

    # With custom types including application/x-custom
    middleware_custom = compress(compressible_types=frozenset({"application/x-custom"}))
    wrapped_custom = cast(RSGIHTTPHandler, middleware_custom(handler))

    proto2 = MockHTTPProtocol()
    scope2 = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped_custom(scope2, proto2)

    headers_dict2 = dict(proto2.response_headers or [])
    assert headers_dict2.get("content-encoding") == "gzip"


@pytest.mark.asyncio
async def test_response_bytes() -> None:
    """Test compression works with response_bytes."""
    body = b"x" * 1000

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_bytes(200, [("content-type", "application/json")], body)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "gzip"

    assert proto.response_body is not None
    decompressed = bytes(gzip.decompress(proto.response_body))
    assert decompressed == body


@pytest.mark.asyncio
async def test_empty_response_not_compressed() -> None:
    """Test empty responses are not compressed."""

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_empty(204, [])

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    assert proto.response_status == 204
    assert proto.response_body == b""


@pytest.mark.asyncio
async def test_content_length_updated() -> None:
    """Test content-length header is updated after compression."""
    body = '{"data": "' + "x" * 1000 + '"}'

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(
            200,
            [
                ("content-type", "application/json"),
                ("content-length", str(len(body))),
            ],
            body,
        )

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert proto.response_body is not None
    assert headers_dict.get("content-length") == str(len(proto.response_body))


def test_default_compressible_types() -> None:
    """Test default compressible types are sensible."""
    assert "application/json" in DEFAULT_COMPRESSIBLE_TYPES
    assert "text/html" in DEFAULT_COMPRESSIBLE_TYPES
    assert "text/css" in DEFAULT_COMPRESSIBLE_TYPES
    assert "text/javascript" in DEFAULT_COMPRESSIBLE_TYPES
    assert "application/javascript" in DEFAULT_COMPRESSIBLE_TYPES
    assert "image/svg+xml" in DEFAULT_COMPRESSIBLE_TYPES
    assert "text/event-stream" in DEFAULT_COMPRESSIBLE_TYPES


def test_default_min_size() -> None:
    """Test default min_size is reasonable."""
    assert DEFAULT_MIN_SIZE == 500


# --- Streaming compression tests ----------------------------------------------
@pytest.mark.asyncio
async def test_stream_compression_zstd() -> None:
    """Test streaming compression with zstd."""
    chunks = [b"hello ", b"world ", b"streaming!"]

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "text/plain")])
        for chunk in chunks:
            await stream.send_bytes(chunk)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "zstd"})
    await wrapped(scope, proto)

    # Check headers
    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "zstd"
    assert headers_dict.get("vary") == "accept-encoding"

    # Decompress and verify
    assert proto.stream_transport is not None
    compressed_data = proto.stream_transport.get_data()
    decompressed = bytes(zstd.decompress(compressed_data))
    assert decompressed == b"hello world streaming!"


@pytest.mark.asyncio
async def test_stream_compression_brotli() -> None:
    """Test streaming compression with brotli."""
    chunks = [b"chunk1", b"chunk2", b"chunk3"]

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "application/json")])
        for chunk in chunks:
            await stream.send_bytes(chunk)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "br"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "br"

    assert proto.stream_transport is not None
    compressed_data = proto.stream_transport.get_data()
    decompressed = bytes(brotli.decompress(compressed_data))
    assert decompressed == b"chunk1chunk2chunk3"


@pytest.mark.asyncio
async def test_stream_compression_gzip() -> None:
    """Test streaming compression with gzip."""
    chunks = [b"a" * 100, b"b" * 100]

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "text/html")])
        for chunk in chunks:
            await stream.send_bytes(chunk)

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "gzip"

    assert proto.stream_transport is not None
    compressed_data = proto.stream_transport.get_data()
    decompressed = bytes(gzip.decompress(compressed_data))
    assert decompressed == b"a" * 100 + b"b" * 100


@pytest.mark.asyncio
async def test_stream_send_str() -> None:
    """Test streaming compression with send_str."""

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "text/plain")])
        await stream.send_str("hello ")
        await stream.send_str("world")

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "zstd"})
    await wrapped(scope, proto)

    assert proto.stream_transport is not None
    compressed_data = proto.stream_transport.get_data()
    decompressed = bytes(zstd.decompress(compressed_data))
    assert decompressed == b"hello world"


@pytest.mark.asyncio
async def test_stream_no_compression_without_encoding() -> None:
    """Test streaming without compression when no encoding accepted."""

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "text/plain")])
        await stream.send_bytes(b"hello")
        await stream.send_bytes(b"world")

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={})  # No accept-encoding
    await wrapped(scope, proto)

    # Should pass through uncompressed
    headers_dict = dict(proto.response_headers or [])
    assert "content-encoding" not in headers_dict

    assert proto.stream_transport is not None
    data = proto.stream_transport.get_data()
    assert data == b"helloworld"


@pytest.mark.asyncio
async def test_stream_no_compression_for_non_compressible_type() -> None:
    """Test streaming with non-compressible content-type passes through uncompressed."""

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(200, [("content-type", "image/png")])
        await stream.send_bytes(b"fake png data")

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    # Should pass through uncompressed
    headers_dict = dict(proto.response_headers or [])
    assert "content-encoding" not in headers_dict

    assert proto.stream_transport is not None
    data = proto.stream_transport.get_data()
    assert data == b"fake png data"


@pytest.mark.asyncio
async def test_stream_no_compression_with_existing_content_encoding() -> None:
    """Test streaming with existing content-encoding passes through uncompressed."""

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        stream = proto.response_stream(
            200,
            [("content-type", "application/json"), ("content-encoding", "br")],
        )
        await stream.send_bytes(b"already compressed")

    middleware = compress()
    wrapped = cast(RSGIHTTPHandler, middleware(handler))

    proto = MockHTTPProtocol()
    scope = mock_scope(headers={"accept-encoding": "gzip"})
    await wrapped(scope, proto)

    # Should pass through without adding another content-encoding
    headers_dict = dict(proto.response_headers or [])
    assert headers_dict.get("content-encoding") == "br"

    assert proto.stream_transport is not None
    data = proto.stream_transport.get_data()
    assert data == b"already compressed"
