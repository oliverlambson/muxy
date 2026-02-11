# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy[compress]",
#     "granian[uvloop]>=2.6.0,<3.0.0",
#     "httpx>=0.28.1,<0.29.0",
# ]
#
# [tool.uv.sources]
# muxy = { path = "../", editable = true }
# ///
"""RSGI compression middleware demo.

Shows usage of compression middleware on an RSGI app, demos simple & SSE streaming
response.
"""

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

import httpx
import uvloop
from granian.rsgi import ProtocolClosed
from granian.server.embed import Server

from muxy import Router
from muxy.middleware.compress import compress
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler

if TYPE_CHECKING:
    app: RSGIHTTPHandler

ADDRESS = "127.0.0.1"
PORT = 8000


async def hello(scope: HTTPScope, proto: HTTPProtocol) -> None:
    body = b"hello world " * 50
    proto.response_bytes(200, [("content-type", "text/plain")], body)


async def stream(scope: HTTPScope, proto: HTTPProtocol) -> None:
    transport = proto.response_stream(200, [("content-type", "text/event-stream")])

    for i in range(1, 11):
        try:
            await transport.send_str(f"data: message {i}\n\n")
        except ProtocolClosed:
            print("client disconnected", flush=True, file=sys.stderr)
            break
        except asyncio.CancelledError:
            print("handler cancelled", flush=True, file=sys.stderr)
            break

        try:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("handler cancelled", flush=True, file=sys.stderr)
            break


async def not_found(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_bytes(404, [("content-type", "text/plain")], b"Not found")


async def not_allowed(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_bytes(405, [("content-type", "text/plain")], b"Method not allowed")


router = Router()
router.use(compress())
router.not_found(not_found)
router.method_not_allowed(not_allowed)
router.get("/", hello)
router.get("/stream", stream)


async def main() -> None:
    """Script entrypoint"""
    logging.basicConfig(level=logging.INFO)
    task = asyncio.create_task(serve())
    await asyncio.sleep(0.1)
    await requests()
    task.cancel()


async def serve() -> None:
    """Runtime for the RSGI-app."""
    server = Server(router, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        await server.shutdown()


async def requests() -> None:
    base_url = f"http://{ADDRESS}:{PORT}"

    # httpx supports gzip out of the box
    async with httpx.AsyncClient(base_url=base_url) as client:
        print("--- Simple response ---")
        response = await client.get("/")
        encoding = response.headers.get("content-encoding")
        print("response compression:", encoding)
        print(response.text, flush=True, file=sys.stderr)

        print("--- SSE streaming response ---")
        async with client.stream("GET", "/stream") as response:
            encoding = response.headers.get("content-encoding")
            print("response compression:", encoding)
            async for chunk in response.aiter_text():
                print(chunk, end="", flush=True, file=sys.stderr)


if __name__ == "__main__":
    uvloop.run(main())
