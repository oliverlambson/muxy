"""Integration test: compress middleware + real granian server.

Reproduces RSGIProtocolClosed raised in _CompressingHTTPStreamTransport.send_bytes
when the client disconnects mid-stream while compression is active.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from granian._granian import RSGIProtocolClosed
from granian.server.embed import Server

from muxy.middleware.compress import compress
from muxy.router import Router
from muxy.rsgi import HTTPProtocol, HTTPScope


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _not_found(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("content-type", "text/plain")], "not found")


async def _method_not_allowed(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(405, [("content-type", "text/plain")], "method not allowed")


@asynccontextmanager
async def run_server(router: Router) -> AsyncIterator[int]:
    """Start a granian embedded server, yield the port, then clean up."""
    port = _get_free_port()
    server = Server(router, address="127.0.0.1", port=port)
    task = asyncio.create_task(server.serve())

    # Wait for TCP readiness
    for _ in range(100):
        try:
            _, w = await asyncio.open_connection("127.0.0.1", port)
            w.close()
            await w.wait_closed()
            break
        except (ConnectionRefusedError, OSError):
            await asyncio.sleep(0.1)
    else:
        task.cancel()
        pytest.fail("Server did not start within 10s")

    try:
        yield port
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_compress_stream_client_disconnect() -> None:
    """Compress middleware should not raise when client disconnects mid-stream.

    Without the fix, RSGIProtocolClosed propagates from
    _CompressingHTTPStreamTransport.send_bytes through compressed_handler
    all the way up to granian, which logs it as an unhandled application error.
    """
    errors: list[RSGIProtocolClosed] = []
    handler_done = asyncio.Event()

    def error_recorder(handler):
        """Outer middleware that observes unhandled errors from compress."""

        async def wrapped(scope, proto):
            try:
                await handler(scope, proto)
            except RSGIProtocolClosed as exc:
                errors.append(exc)
            finally:
                handler_done.set()

        return wrapped

    async def sse_handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        transport = proto.response_stream(
            200,
            [("content-type", "text/event-stream"), ("cache-control", "no-cache")],
        )
        for i in range(200):
            await transport.send_str(f"data: {'x' * 500} message {i}\n\n")
            await asyncio.sleep(0.02)

    router = Router()
    router.not_found(_not_found)
    router.method_not_allowed(_method_not_allowed)
    router.use(error_recorder)  # outermost — catches errors from compress
    router.use(compress())
    router.get("/sse", sse_handler)
    router.finalize()

    async with run_server(router) as port:
        # Connect with Accept-Encoding to trigger compression
        _reader, writer = await asyncio.open_connection("127.0.0.1", port)
        request = (
            f"GET /sse HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            f"Accept-Encoding: gzip\r\n"
            f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        # Let the server start streaming compressed data
        await asyncio.sleep(0.3)

        # Disconnect mid-stream
        writer.close()
        await writer.wait_closed()

        # Wait for handler to finish (or error out)
        await asyncio.wait_for(handler_done.wait(), timeout=10.0)

    # Compress middleware should handle disconnect gracefully
    assert errors == [], (
        f"Unhandled error(s) in compress middleware: "
        f"{[f'{type(e).__name__}: {e}' for e in errors]}"
    )
