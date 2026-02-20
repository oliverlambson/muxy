# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy[otel]",
#     "granian[uvloop]>=2.6.0,<3.0.0",
#     "httpx>=0.28.1,<0.29.0",
#     "opentelemetry-sdk>=1.39.1,<2.0.0",
# ]
#
# [tool.uv.sources]
# muxy = { path = "../", editable = true }
# ///
"""RSGI OpenTelemetry tracing middleware demo.

Shows usage of otel middleware with an in-memory exporter so traces can be
printed to the console without needing an external collector.
"""

import asyncio
import logging
import sys

import httpx
import uvloop
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from muxy import Router, path_params
from muxy.middleware.otel import otel
from muxy.rsgi import HTTPProtocol, HTTPScope

ADDRESS = "127.0.0.1"
PORT = 8000


# --- handlers ---
async def hello(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(200, [("content-type", "text/plain")], "hello world")


async def greet(scope: HTTPScope, proto: HTTPProtocol) -> None:
    name = path_params.get()["name"]
    proto.response_str(200, [("content-type", "text/plain")], f"hello {name}")


async def not_found(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("content-type", "text/plain")], "not found")


async def not_allowed(scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(405, [("content-type", "text/plain")], "method not allowed")


# --- app setup ---
exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))

trace_middleware = otel(tracer_provider=provider)

router = Router()
router.use(trace_middleware)
# NOTE: Error handlers bypass route middleware, so wrap them explicitly if you
# want tracing for 404/405 requests.
router.not_found(trace_middleware(not_found))
router.method_not_allowed(trace_middleware(not_allowed))
router.get("/", hello)
router.get("/greet/{name}", greet)


# --- run ---
async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    task = asyncio.create_task(serve())
    await asyncio.sleep(0.1)
    await requests()
    provider.shutdown()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def serve() -> None:
    from granian.server.embed import Server

    server = Server(router, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        await server.shutdown()


async def requests() -> None:
    base_url = f"http://{ADDRESS}:{PORT}"

    async with httpx.AsyncClient(base_url=base_url) as client:
        print("--- GET / ---", file=sys.stderr)
        await client.get("/")

        print("--- GET /greet/world ---", file=sys.stderr)
        await client.get("/greet/world")

        print("--- GET /greet/muxy ---", file=sys.stderr)
        await client.get("/greet/muxy")

        print("--- GET /nonexistent ---", file=sys.stderr)
        await client.get("/nonexistent")

        print("--- DELETE / (method not allowed) ---", file=sys.stderr)
        await client.delete("/")

    print("--- Collected spans ---", file=sys.stderr)
    for span in exporter.get_finished_spans():
        attrs = span.attributes or {}
        print(
            f"  {span.name:<30} "
            f"status={attrs['http.response.status_code']:<4} "
            f"route={attrs.get('http.route', ''):<20} "  # not set on 404/405
            f"path={attrs['url.path']}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    uvloop.run(main())
