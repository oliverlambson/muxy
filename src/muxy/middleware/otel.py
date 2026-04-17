"""OpenTelemetry tracing and metrics middleware.

Creates HTTP server spans and metrics with semantic conventions for each request.

Install with: uv add "muxy[otel]"
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Literal, cast, overload

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

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

type _CapturedSpanAttribute = Literal["client.port"]
type _SpanAttributeValue = str | int | tuple[str, ...]

_DEFAULT_REQUEST_HEADERS = (
    "referer",
    "sec-fetch-site",
    "sec-fetch-mode",
    "sec-fetch-dest",
)
_SUPPORTED_CAPTURED_SPAN_ATTRIBUTES = frozenset(("client.port",))


def _split_endpoint(value: str) -> tuple[str | None, int | None]:
    value = value.strip()
    if not value:
        return None, None

    if value.startswith("["):
        bracket_end = value.find("]")
        if bracket_end != -1:
            host = value[1:bracket_end]
            remainder = value[bracket_end + 1 :]
            if remainder.startswith(":") and remainder[1:].isdigit():
                return host or None, int(remainder[1:])
            return host or None, None

    if value.count(":") == 1:
        host, port = value.rsplit(":", maxsplit=1)
        if host and port.isdigit():
            return host, int(port)

    return value, None


def _capture_request_headers(
    headers: Mapping[str, str], header_allowlist: tuple[str, ...]
) -> dict[str, tuple[str, ...]]:
    attributes: dict[str, tuple[str, ...]] = {}
    for header_name in header_allowlist:
        header_value = headers.get(header_name)
        if header_value:
            attributes[f"http.request.header.{header_name}"] = (header_value,)
    return attributes


def _normalize_captured_span_attributes(
    captured_span_attributes: tuple[_CapturedSpanAttribute, ...],
) -> frozenset[_CapturedSpanAttribute]:
    normalized = frozenset(
        attribute.strip().lower()
        for attribute in captured_span_attributes
        if attribute.strip()
    )
    unsupported = normalized - _SUPPORTED_CAPTURED_SPAN_ATTRIBUTES
    if unsupported:
        unsupported_values = ", ".join(sorted(unsupported))
        supported_values = ", ".join(sorted(_SUPPORTED_CAPTURED_SPAN_ATTRIBUTES))
        msg = (
            "Unsupported captured_span_attributes: "
            f"{unsupported_values}. Supported values: {supported_values}"
        )
        raise ValueError(msg)
    return cast("frozenset[_CapturedSpanAttribute]", normalized)


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
    captured_request_headers: tuple[str, ...] = _DEFAULT_REQUEST_HEADERS,
    captured_span_attributes: tuple[_CapturedSpanAttribute, ...] = (),
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
        captured_request_headers: Explicit request-header allowlist to copy onto
            spans as ``http.request.header.<key>`` attributes. Defaults to the
            small browser-debugging set of ``referer`` and ``sec-fetch-*``.
            Pass ``()`` to disable request-header capture entirely.
        captured_span_attributes: Explicit allowlist of extra span attributes to
            capture. Supported values: ``"client.port"``. Defaults to ``()``.

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
    header_allowlist = tuple(
        dict.fromkeys(
            header.strip().lower()
            for header in captured_request_headers
            if header.strip()
        )
    )
    span_attribute_allowlist = _normalize_captured_span_attributes(
        captured_span_attributes
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
            client_address, client_port = _split_endpoint(scope.client)
            peer_source = cast("str | None", getattr(scope, "network_peer", None))
            peer_address: str | None = None
            peer_port: int | None = None
            if peer_source is not None:
                peer_address, peer_port = _split_endpoint(peer_source)

            attributes: dict[str, _SpanAttributeValue] = {
                "http.request.method": method,
                "url.path": scope.path,
                "url.scheme": scope.scheme,
                "network.protocol.version": scope.http_version,
                "server.address": scope.server,
            }
            if client_address is not None:
                attributes["client.address"] = client_address
            if "client.port" in span_attribute_allowlist and client_port is not None:
                attributes["client.port"] = client_port
            if peer_address is not None:
                attributes["network.peer.address"] = peer_address
            if peer_port is not None:
                attributes["network.peer.port"] = peer_port
            if route:
                attributes["http.route"] = route
            if scope.query_string:
                attributes["url.query"] = scope.query_string
            user_agent = scope.headers.get("user-agent")
            if user_agent is not None:
                attributes["user_agent.original"] = user_agent
            attributes.update(_capture_request_headers(scope.headers, header_allowlist))
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
                error_type: str | None = None
                try:
                    await handler(scope, wrapped_proto)
                except Exception as exc:
                    error_type = type(exc).__name__
                    span.set_attribute("error.type", error_type)
                    raise
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
                            if error_type is None:
                                span.set_attribute(
                                    "error.type",
                                    str(wrapped_proto._status),
                                )
                    duration_histogram.record(duration, duration_attrs)

        return traced_handler

    return middleware
