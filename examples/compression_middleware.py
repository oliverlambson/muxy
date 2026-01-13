# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy[compress] @ file:///${PROJECT_ROOT}/../muxy",
#     "granian[uvloop]>=2.6.0,<3.0.0",
#     "httpx>=0.28.1,<0.29.0",
# ]
# ///
"""RSGI compression middleware demo.

Shows useage of compression middleware on an RSGI app, demos simple & streaming
response.
"""

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

import httpx
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
    transport = proto.response_stream(200, [("content-type", "text/plain")])

    rate = 1 / 30  # 30 fps
    i = 1
    abs_incr = 1
    incr = abs_incr
    while True:
        if i <= 1:
            incr = abs_incr
        elif i >= 15:
            incr = -abs_incr

        try:
            await transport.send_str("#" * (6 * i) + "\n")
        except ProtocolClosed:
            print("client disconnected", flush=True, file=sys.stderr)
            break
        except asyncio.CancelledError:
            print("handler cancelled", flush=True, file=sys.stderr)
            break

        i += incr

        try:
            await asyncio.sleep(rate)
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
router.finalize()


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
        print("server shutdown", flush=True, file=sys.stderr)


async def requests() -> None:
    base_url = f"http://{ADDRESS}:{PORT}"

    # httpx supports gzip out of the box
    async with httpx.AsyncClient(base_url=base_url) as client:
        print("--- Simple response ---")
        response = await client.get("/")
        encoding = response.headers.get("content-encoding")
        print("response compression:", encoding)
        print(response.text, flush=True, file=sys.stderr)

        print("--- Streaming response ---")
        try:
            async with asyncio.timeout(1):
                async with client.stream("GET", "/stream") as response:
                    encoding = response.headers.get("content-encoding")
                    print("response compression:", encoding)
                    async for chunk in response.aiter_text():
                        print(chunk, end="", flush=True, file=sys.stderr)
        except TimeoutError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
