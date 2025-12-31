from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal, NotRequired, TypedDict

type HTTPMethod = Literal[
    "GET", "PUT", "PATCH", "POST", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"
]


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    version: str
    spec_version: NotRequired[str]
    state: NotRequired[dict[str, Any]]


class HTTPScope(TypedDict):
    type: Literal["http"]
    version: str
    spec_version: NotRequired[str]
    http_version: Literal["1.0", "1.1", "2"]
    method: HTTPMethod
    scheme: str
    path: str
    raw_path: NotRequired[bytes]
    query_string: bytes
    root_path: NotRequired[str]
    headers: Iterable[tuple[bytes, bytes]]
    client: NotRequired[Iterable[tuple[str, int]]]
    server: NotRequired[Iterable[tuple[str, int | None]]]
    state: NotRequired[dict[str, Any]]


class WebsocketScope(TypedDict):
    type: Literal["websocket"]
    version: str
    spec_version: NotRequired[str]
    http_version: Literal["1.0", "1.1", "2"]
    scheme: str
    path: str
    raw_path: NotRequired[bytes]
    query_string: bytes
    root_path: NotRequired[str]
    headers: Iterable[tuple[bytes, bytes]]
    client: NotRequired[Iterable[tuple[str, int]]]
    server: NotRequired[Iterable[tuple[str, int | None]]]
    subprotocols: NotRequired[Iterable[str]]
    state: NotRequired[dict[str, Any]]


class HTTPRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HTTPResponseStartEvent(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[Iterable[tuple[bytes, bytes]]]
    trailers: NotRequired[bool]


class HTTPResponseBodyEvent(TypedDict):
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HTTPDisconnectEvent(TypedDict):
    type: Literal["http.disconnect"]


type ReceiveHTTPEvent = HTTPRequestEvent | HTTPDisconnectEvent
type SendHTTPEvent = HTTPResponseStartEvent | HTTPResponseBodyEvent


class WebsocketConnectEvent(TypedDict):
    type: Literal["websocket.connect"]


class WebsocketAcceptEvent(TypedDict):
    type: Literal["websocket.accept"]
    subprotocol: NotRequired[str]
    headers: NotRequired[Iterable[tuple[bytes, bytes]]]


class WebsocketReceiveEvent(TypedDict):
    type: Literal["websocket.receive"]
    bytes: NotRequired[bytes]
    text: NotRequired[str]


class WebsocketSendEvent(TypedDict):
    type: Literal["websocket.send"]
    bytes: NotRequired[bytes]
    text: NotRequired[str]


class WebsocketDisconnectEvent(TypedDict):
    type: Literal["websocket.disconnect"]
    code: int
    reason: NotRequired[str]


class WebsocketCloseEvent(TypedDict):
    type: Literal["websocket.close"]
    code: NotRequired[int]
    reason: NotRequired[str]


type ReceiveWebsocketEvent = (
    WebsocketConnectEvent | WebsocketReceiveEvent | WebsocketDisconnectEvent
)
type SendWebsocketEvent = (
    WebsocketAcceptEvent | WebsocketSendEvent | WebsocketCloseEvent
)


class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifespanStartupCompleteEvent(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailedEvent(TypedDict):
    type: Literal["lifespan.startup.failed"]
    message: NotRequired[str]


class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


class LifespanShutdownCompleteEvent(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailedEvent(TypedDict):
    type: Literal["lifespan.shutdown.failed"]
    message: NotRequired[str]


type ReceiveLifespanEvent = LifespanStartupEvent | LifespanShutdownEvent
type SendLifespanEvent = (
    LifespanStartupCompleteEvent
    | LifespanStartupFailedEvent
    | LifespanShutdownCompleteEvent
    | LifespanShutdownFailedEvent
)


type HTTPReceive = Callable[[], Awaitable[ReceiveHTTPEvent]]
type WebsocketReceive = Callable[[], Awaitable[ReceiveWebsocketEvent]]
type LifespanReceive = Callable[[], Awaitable[ReceiveLifespanEvent]]

type HTTPSend = Callable[[SendHTTPEvent], Awaitable[None]]
type WebsocketSend = Callable[[SendWebsocketEvent], Awaitable[None]]
type LifespanSend = Callable[[SendLifespanEvent], Awaitable[None]]

type ASGIHTTPHandler = Callable[[HTTPScope, HTTPReceive, HTTPSend], Awaitable[None]]
type ASGIWebsocketHandler = Callable[
    [WebsocketScope, WebsocketReceive, WebsocketSend], Awaitable[None]
]
type ASGIHandler = ASGIHTTPHandler | ASGIWebsocketHandler
