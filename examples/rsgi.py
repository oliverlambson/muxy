# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "granian[uvloop]>=2.6.0,<3.0.0",
#     "httpx>=0.28.1,<0.29.0",
#     "httpx-ws>=0.8.2,<0.9.0",
# ]
# ///
"""RSGI app demo.

Shows implementation of a pure RSGI app, runs it with Granian, and successfully
sends HTTP and Websocket requests to that running webserver.
"""

import asyncio
import logging
import sys
from typing import cast

import httpx
import uvloop
from granian.rsgi import HTTPProtocol, Scope, WebsocketProtocol
from granian.server.embed import Server
from httpx_ws import aconnect_ws

ADDRESS = "127.0.0.1"
PORT = 8000


async def main() -> None:
    """Script entrypoint"""
    logging.basicConfig(level=logging.INFO)
    task = asyncio.create_task(serve())
    await requests()
    task.cancel()


async def serve() -> None:
    """Runtime for the RSGI-app."""
    server = Server(app, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        await server.shutdown()


async def app(scope: Scope, proto: HTTPProtocol | WebsocketProtocol) -> None:
    """An RSGI-compliant app.

    This is where the router logic would live: it would identify & construct the correct
    handler given the scope, and pass the scope & proto in to it.
    """
    if scope.proto == "http":
        print("HTTP", flush=True, file=sys.stderr)
        proto = cast(HTTPProtocol, proto)
        print(_fmt_scope(scope), flush=True, file=sys.stderr)
        proto.response_str(200, [], _fmt_scope(scope))
    elif scope.proto == "ws":
        print("WEBSOCKET", flush=True, file=sys.stderr)
        proto = cast(WebsocketProtocol, proto)
        print(_fmt_scope(scope), flush=True, file=sys.stderr)
        transport = await proto.accept()
        await transport.send_str(_fmt_scope(scope))
    print(flush=True, file=sys.stderr)


def _fmt_scope(scope: Scope) -> str:
    return f"""\
proto={scope.proto}
http_version={scope.http_version}
rsgi_version={scope.rsgi_version}
server={scope.server}
client={scope.client}
scheme={scope.scheme}
method={scope.method}
path={scope.path}
query_string={scope.query_string}
headers={scope.headers.items()}
authority={scope.authority}"""


async def requests() -> None:
    """Sends client HTTP/Websocket requests to the running server."""
    base_url = f"http://{ADDRESS}:{PORT}"
    path = "/"
    async with httpx.AsyncClient(base_url=base_url) as client:
        for method in [
            "CONNECT",
            "DELETE",
            "GET",
            "HEAD",
            "OPTIONS",
            "PATCH",
            "POST",
            "PUT",
            "TRACE",
        ]:
            _ = (await (await client.request(method, path)).aread()).decode()
        async with aconnect_ws(path, client) as client:
            _ = await client.receive_text()


if __name__ == "__main__":
    uvloop.run(main())
