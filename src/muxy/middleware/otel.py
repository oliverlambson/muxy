"""OpenTelemetry tracing and metrics middleware.

Creates HTTP server spans and metrics with semantic conventions for each request.

Install with: uv add "muxy[otel]"
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from collections.abc import Callable

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
    from opentelemetry import metrics, trace
    from opentelemetry.propagate import extract
    from opentelemetry.trace import (
        SpanKind,
        StatusCode,
        TracerProvider,
    )
except ImportError as e:
    msg = (
        "OpenTelemetry middleware requires the 'otel' extra. "
        "Install with: uv add 'muxy[otel]'"
    )
    raise ImportError(msg) from e

from muxy.tree import http_route, path_params


class _TracingHTTPProtocol:
    """Wraps HTTPProtocol to capture response status code for the span."""

    __slots__ = ("_proto", "_status")

    def __init__(self, proto: HTTPProtocol) -> None:
        self._proto = proto
        self._status: int | None = None

    async def __call__(self) -> bytes:
        return await self._proto()

    def __aiter__(self) -> bytes:
        return self._proto.__aiter__()

    async def client_disconnect(self) -> None:
        await self._proto.client_disconnect()

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None:
        self._status = status
        self._proto.response_empty(status, headers)

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        self._status = status
        self._proto.response_str(status, headers, body)

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self._status = status
        self._proto.response_bytes(status, headers, body)

    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None:
        self._status = status
        self._proto.response_file(status, headers, file)

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        self._status = status
        self._proto.response_file_range(status, headers, file, start, end)

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> HTTPStreamTransport:
        self._status = status
        return self._proto.response_stream(status, headers)


_DURATION_BUCKETS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
)


def otel(
    *,
    tracer_provider: TracerProvider | None = None,
    meter_provider: metrics.MeterProvider | None = None,
) -> Callable[[RSGIHandler], RSGIHandler]:
    """Create OpenTelemetry tracing and metrics middleware.

    Creates server spans and metrics with HTTP semantic conventions for each
    HTTP request. Websocket requests pass through without instrumentation.

    Extracts trace context from incoming request headers (e.g. ``traceparent``)
    for distributed tracing. Only depends on ``opentelemetry-api``; users bring
    their own SDK and exporters.

    Metrics emitted:
        - ``http.server.request.duration`` (histogram, seconds)
        - ``http.server.active_requests`` (up-down counter)

    Args:
        tracer_provider: Optional TracerProvider. If None, uses the global provider.
        meter_provider: Optional MeterProvider. If None, uses the global provider.

    Returns:
        Middleware function that wraps handlers with tracing and metrics.

    Example:
        router.use(otel())

        # With custom providers
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.metrics import MeterProvider
        router.use(otel(
            tracer_provider=TracerProvider(),
            meter_provider=MeterProvider(),
        ))
    """
    tracer = trace.get_tracer(
        "muxy",
        tracer_provider=tracer_provider,
    )
    meter = metrics.get_meter(
        "muxy",
        meter_provider=meter_provider,
    )
    duration_histogram = meter.create_histogram(
        "http.server.request.duration",
        unit="s",
        description="Duration of HTTP server requests.",
        explicit_bucket_boundaries_advisory=_DURATION_BUCKETS,
    )
    active_requests_counter = meter.create_up_down_counter(
        "http.server.active_requests",
        unit="{request}",
        description="Number of active HTTP server requests.",
    )

    def middleware(handler: RSGIHandler) -> RSGIHandler:
        @overload
        async def traced_handler(scope: HTTPScope, proto: HTTPProtocol) -> None: ...
        @overload
        async def traced_handler(
            scope: WebsocketScope, proto: WebsocketProtocol
        ) -> None: ...
        async def traced_handler(
            scope: WebsocketScope | HTTPScope,
            proto: HTTPProtocol | WebsocketProtocol,
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

            # Extract propagated context from request headers
            ctx = extract(scope.headers)

            # Read http.route from ContextVar (set by Router before middleware runs)
            route = http_route.get("")

            # Build span name: "METHOD /route" for matched, placeholder for unmatched
            method = scope.method
            span_name = f"{method} {route}" if route else method

            # Span attributes (stable HTTP semantic conventions)
            attributes: dict[str, str | int] = {
                "http.request.method": method,
                "url.path": scope.path,
                "url.scheme": scope.scheme,
                "network.protocol.version": scope.http_version,
                "server.address": scope.server,
                "client.address": scope.client,
            }
            if route:
                attributes["http.route"] = route
            if scope.query_string:
                attributes["url.query"] = scope.query_string
            user_agent = scope.headers.get("user-agent")
            if user_agent is not None:
                attributes["user_agent.original"] = user_agent
            # below isn't part of semantic conventions but having path params is useful
            params = path_params.get({})
            for key, value in params.items():
                attributes[f"http.route.param.{key}"] = value

            # Metric attributes (required + conditionally required per spec)
            active_attrs: dict[str, str | int] = {
                "http.request.method": method,
                "url.scheme": scope.scheme,
            }
            if route:
                active_attrs["http.route"] = route

            active_requests_counter.add(1, active_attrs)
            start = time.perf_counter()

            with tracer.start_as_current_span(
                span_name,
                context=ctx,
                kind=SpanKind.SERVER,
                attributes=attributes,
                record_exception=True,
                set_status_on_exception=True,
            ) as span:
                wrapped_proto = _TracingHTTPProtocol(proto)
                try:
                    await handler(scope, wrapped_proto)
                finally:
                    duration = time.perf_counter() - start
                    active_requests_counter.add(-1, active_attrs)
                    duration_attrs = dict(active_attrs)
                    if wrapped_proto._status is not None:
                        span.set_attribute(
                            "http.response.status_code",
                            wrapped_proto._status,
                        )
                        duration_attrs["http.response.status_code"] = (
                            wrapped_proto._status
                        )
                        if not route:
                            span.update_name(f"{method} {wrapped_proto._status}")
                        if wrapped_proto._status >= 500:
                            span.set_status(StatusCode.ERROR)
                    duration_histogram.record(duration, duration_attrs)

        return traced_handler

    return middleware
