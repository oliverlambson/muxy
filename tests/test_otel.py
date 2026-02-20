from typing import Any, cast

import pytest
from conftest import MockHTTPProtocol, mock_scope
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from muxy.middleware.otel import otel
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler
from muxy.tree import http_route, path_params


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def provider(exporter: InMemorySpanExporter) -> TracerProvider:
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exporter))
    return tp


@pytest.fixture
def metric_reader() -> InMemoryMetricReader:
    return InMemoryMetricReader()


@pytest.fixture
def meter_provider(metric_reader: InMemoryMetricReader) -> MeterProvider:
    return MeterProvider(metric_readers=[metric_reader])


# --- Basic span creation ---


@pytest.mark.asyncio
async def test_basic_span(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [("content-type", "text/plain")], "ok")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/hello", method="GET")
    proto = MockHTTPProtocol()

    with http_route.set("/hello"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "GET /hello"
    assert span.kind == SpanKind.SERVER
    assert span.attributes is not None
    assert span.attributes["http.request.method"] == "GET"
    assert span.attributes["url.path"] == "/hello"
    assert span.attributes["http.response.status_code"] == 200
    assert span.attributes["http.route"] == "/hello"


@pytest.mark.asyncio
async def test_span_name_with_route_pattern(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [], "ok")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/user/123", method="GET")
    proto = MockHTTPProtocol()

    with http_route.set("/user/{id}"), path_params.set({"id": "123"}):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].name == "GET /user/{id}"
    assert spans[0].attributes is not None
    assert spans[0].attributes["http.route"] == "/user/{id}"
    assert spans[0].attributes["url.path"] == "/user/123"
    assert spans[0].attributes["http.route.param.id"] == "123"


@pytest.mark.asyncio
async def test_path_params_multiple(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [], "ok")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/user/42/post/99", method="GET")
    proto = MockHTTPProtocol()

    with (
        http_route.set("/user/{id}/post/{post_id}"),
        path_params.set({"id": "42", "post_id": "99"}),
    ):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].attributes is not None
    assert spans[0].attributes["http.route.param.id"] == "42"
    assert spans[0].attributes["http.route.param.post_id"] == "99"


@pytest.mark.asyncio
async def test_span_name_without_route(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(404, [], "not found")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/missing", method="GET")
    proto = MockHTTPProtocol()

    with http_route.set(""):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].name == "GET 404"
    assert spans[0].attributes is not None
    assert "http.route" not in spans[0].attributes


# --- Status code handling ---


@pytest.mark.asyncio
async def test_5xx_sets_error_status(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(500, [], "internal server error")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code == StatusCode.ERROR


@pytest.mark.asyncio
async def test_4xx_does_not_set_error(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(404, [], "not found")

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code == StatusCode.UNSET


# --- Exception handling ---


@pytest.mark.asyncio
async def test_exception_records_and_raises(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with pytest.raises(RuntimeError, match="boom"), http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code == StatusCode.ERROR
    assert len(spans[0].events) > 0
    exception_event = next(e for e in spans[0].events if e.name == "exception")
    assert exception_event.attributes is not None
    assert exception_event.attributes["exception.type"] == "RuntimeError"


# --- Websocket passthrough ---


@pytest.mark.asyncio
async def test_websocket_passthrough(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    called = False

    async def handler(scope, proto) -> None:
        nonlocal called
        called = True

    mw = otel(tracer_provider=provider)
    wrapped = mw(handler)

    class FakeWsScope:
        proto = "ws"
        method = "GET"
        path = "/"

    await wrapped(FakeWsScope(), None)  # ty: ignore[invalid-argument-type]

    assert called
    assert len(exporter.get_finished_spans()) == 0


# --- Attributes ---


@pytest.mark.asyncio
async def test_attributes_populated(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_empty(204, [])

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(
        path="/search",
        method="POST",
        headers={
            "user-agent": "test-agent/1.0",
        },
    )
    # Set query_string on the mock
    scope.query_string = "q=hello"
    proto = MockHTTPProtocol()

    with http_route.set("/search"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    attrs = spans[0].attributes
    assert attrs is not None
    assert attrs["http.request.method"] == "POST"
    assert attrs["url.path"] == "/search"
    assert attrs["url.scheme"] == "http"
    assert attrs["url.query"] == "q=hello"
    assert attrs["network.protocol.version"] == "1.1"
    assert attrs["server.address"] == "localhost"
    assert attrs["client.address"] == "127.0.0.1"
    assert attrs["user_agent.original"] == "test-agent/1.0"
    assert attrs["http.response.status_code"] == 204


# --- All response methods capture status ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response_method, response_args",
    [
        ("response_empty", (200, [])),
        ("response_str", (201, [("content-type", "text/plain")], "ok")),
        ("response_bytes", (200, [], b"ok")),
        ("response_file", (200, [("content-type", "text/plain")], "/tmp/test.txt")),  # noqa: S108
        (
            "response_file_range",
            (206, [("content-type", "text/plain")], "/tmp/test.txt", 0, 100),  # noqa: S108
        ),
        ("response_stream", (200, [("content-type", "text/event-stream")])),
    ],
)
async def test_response_method_captures_status(
    response_method: str,
    response_args: tuple,
    provider: TracerProvider,
    exporter: InMemorySpanExporter,
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        getattr(proto, response_method)(*response_args)

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    expected_status = response_args[0]
    assert spans[0].attributes is not None
    assert spans[0].attributes["http.response.status_code"] == expected_status


# --- Distributed tracing ---


@pytest.mark.asyncio
async def test_distributed_tracing_propagation(
    provider: TracerProvider, exporter: InMemorySpanExporter
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_empty(200, [])

    mw = otel(tracer_provider=provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    trace_id = "0af7651916cd43dd8448eb211c80319c"
    parent_span_id = "b7ad6b7169203331"
    scope = mock_scope(
        headers={
            "traceparent": f"00-{trace_id}-{parent_span_id}-01",
        }
    )
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    # Verify the span's trace ID matches the propagated one
    assert span.context is not None
    assert f"{span.context.trace_id:032x}" == trace_id
    # Verify parent span ID
    assert span.parent is not None
    assert f"{span.parent.span_id:016x}" == parent_span_id


# --- Custom tracer provider ---


@pytest.mark.asyncio
async def test_custom_tracer_provider() -> None:
    exporter = InMemorySpanExporter()
    custom_provider = TracerProvider()
    custom_provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_empty(200, [])

    mw = otel(tracer_provider=custom_provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "GET /"


# --- Metrics ---


def _get_metric(metric_reader: InMemoryMetricReader, name: str) -> Any:
    """Extract a metric by name from the reader."""
    data = metric_reader.get_metrics_data()
    assert data is not None
    for resource_metric in data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                if metric.name == name:
                    return metric
    msg = f"Metric {name!r} not found"
    raise AssertionError(msg)


@pytest.mark.asyncio
async def test_request_duration_recorded(
    provider: TracerProvider,
    exporter: InMemorySpanExporter,
    meter_provider: MeterProvider,
    metric_reader: InMemoryMetricReader,
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [], "ok")

    mw = otel(tracer_provider=provider, meter_provider=meter_provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/hello", method="GET")
    proto = MockHTTPProtocol()

    with http_route.set("/hello"):
        await wrapped(scope, proto)

    metric = _get_metric(metric_reader, "http.server.request.duration")
    assert metric.unit == "s"
    data_points = list(metric.data.data_points)
    assert len(data_points) == 1
    dp = data_points[0]
    assert dp.sum > 0
    assert dp.count == 1
    assert dp.attributes["http.request.method"] == "GET"
    assert dp.attributes["url.scheme"] == "http"
    assert dp.attributes["http.response.status_code"] == 200
    assert dp.attributes["http.route"] == "/hello"


@pytest.mark.asyncio
async def test_active_requests_incremented_and_decremented(
    provider: TracerProvider,
    exporter: InMemorySpanExporter,
    meter_provider: MeterProvider,
    metric_reader: InMemoryMetricReader,
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(200, [], "ok")

    mw = otel(tracer_provider=provider, meter_provider=meter_provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope()
    proto = MockHTTPProtocol()

    with http_route.set("/"):
        await wrapped(scope, proto)

    # After request completes, active requests should be back to 0 (+1 then -1)
    metric = _get_metric(metric_reader, "http.server.active_requests")
    assert metric.unit == "{request}"
    data_points = list(metric.data.data_points)
    assert len(data_points) == 1
    assert data_points[0].value == 0


@pytest.mark.asyncio
async def test_duration_metric_attributes_without_route(
    provider: TracerProvider,
    exporter: InMemorySpanExporter,
    meter_provider: MeterProvider,
    metric_reader: InMemoryMetricReader,
) -> None:
    async def handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        proto.response_str(404, [], "not found")

    mw = otel(tracer_provider=provider, meter_provider=meter_provider)
    wrapped = cast("RSGIHTTPHandler", mw(handler))

    scope = mock_scope(path="/missing", method="GET")
    proto = MockHTTPProtocol()

    with http_route.set(""):
        await wrapped(scope, proto)

    metric = _get_metric(metric_reader, "http.server.request.duration")
    dp = next(iter(metric.data.data_points))
    assert dp.attributes["http.request.method"] == "GET"
    assert dp.attributes["http.response.status_code"] == 404
    assert "http.route" not in dp.attributes
