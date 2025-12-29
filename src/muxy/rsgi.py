from __future__ import annotations

from asyncio import AbstractEventLoop
from collections.abc import Callable, Mapping
from typing import Literal, Protocol, runtime_checkable


class RSGIHTTPPlain(Protocol):
    async def __rsgi__(self, __scope: HTTPScope, __proto: HTTPProtocol) -> None: ...


class RSGIHTTPWithInit(Protocol):
    async def __rsgi__(self, __scope: HTTPScope, __proto: HTTPProtocol) -> None: ...
    def __rsgi_init__(self, __loop: AbstractEventLoop) -> None: ...


class RSGIHTTPWithDel(Protocol):
    async def __rsgi__(self, __scope: HTTPScope, __proto: HTTPProtocol) -> None: ...
    def __rsgi_del__(self, __loop: AbstractEventLoop) -> None: ...


class RSGIHTTPFull(Protocol):
    async def __rsgi__(self, __scope: HTTPScope, __proto: HTTPProtocol) -> None: ...
    def __rsgi_init__(self, __loop: AbstractEventLoop) -> None: ...
    def __rsgi_del__(self, __loop: AbstractEventLoop) -> None: ...


type RSGIHTTP = RSGIHTTPPlain | RSGIHTTPWithInit | RSGIHTTPWithDel | RSGIHTTPFull


class RSGIWebsocketPlain(Protocol):
    async def __rsgi__(
        self, __scope: WebsocketScope, __proto: WebsocketProtocol
    ) -> None: ...


class RSGIWebsocketWithInit(Protocol):
    async def __rsgi__(
        self, __scope: WebsocketScope, __proto: WebsocketProtocol
    ) -> None: ...
    def __rsgi_init__(self, __loop: AbstractEventLoop) -> None: ...


class RSGIWebsocketWithDel(Protocol):
    async def __rsgi__(
        self, __scope: WebsocketScope, __proto: WebsocketProtocol
    ) -> None: ...
    def __rsgi_init__(self, __loop: AbstractEventLoop) -> None: ...


class RSGIWebsocketFull(Protocol):
    async def __rsgi__(
        self, __scope: WebsocketScope, __proto: WebsocketProtocol
    ) -> None: ...
    def __rsgi_init__(self, __loop: AbstractEventLoop) -> None: ...
    def __rsgi_del__(self, __loop: AbstractEventLoop) -> None: ...


type RSGIWebsocket = (
    RSGIWebsocketPlain
    | RSGIWebsocketWithInit
    | RSGIWebsocketWithDel
    | RSGIWebsocketFull
)

type RSGI = RSGIHTTP | RSGIWebsocket


@runtime_checkable
class RSGIHTTPHandler(Protocol):
    async def __call__(self, __scope: HTTPScope, __proto: HTTPProtocol) -> None: ...


@runtime_checkable
class RSGIWebsocketHandler(Protocol):
    async def __call__(
        self, __scope: WebsocketScope, __proto: WebsocketProtocol
    ) -> None: ...


type RSGIHandler = RSGIHTTPHandler | RSGIWebsocketHandler


type RSGIMiddleware = Callable[[RSGI], RSGI]


class HTTPScope(Protocol):
    proto: Literal["http"]
    http_version: Literal["1", "1.1", "2"]
    rsgi_version: str
    server: str
    client: str
    scheme: str
    method: str
    path: str
    query_string: str
    headers: Mapping[str, str]
    authority: str | None


class WebsocketScope(Protocol):
    proto: Literal["ws"]
    http_version: Literal["1", "1.1", "2"]
    rsgi_version: str
    server: str
    client: str
    scheme: str
    method: str
    path: str
    query_string: str
    headers: Mapping[str, str]
    authority: str | None


type Scope = HTTPScope | WebsocketScope


class HTTPProtocol(Protocol):
    async def __call__(self) -> bytes:
        """whole body"""
        ...

    def __aiter__(self) -> bytes:
        """body chunks"""
        ...

    async def client_disconnect(self) -> None:
        """watch for client disconnection. NB: may not resolve because connection
        lifecycle may be longer than single request lifecycle due to http keepalived
        connections."""
        ...

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None: ...
    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None: ...
    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None: ...
    def response_file(self, status: int, headers: list[tuple[str, str]], file: str):
        """send back contents of file using path for file, application must still set
        correct headers for file"""
        ...

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        """send back file range response using path for file, start inclusive, end
        exclusive, application must still set correct headers for file"""
        ...

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> HTTPStreamTransport:
        """start a stream response"""
        ...


class HTTPStreamTransport(Protocol):
    async def send_bytes(self, data: bytes) -> None: ...
    async def send_str(self, data: str) -> None: ...


class WebsocketProtocol(Protocol):
    async def accept(self) -> WebsocketTransport: ...
    def close(self, status: int | None) -> tuple[int, bool]: ...


class WebsocketTransport(Protocol):
    async def receive(self) -> WebsocketMessage: ...
    async def send_bytes(self, data: bytes) -> None: ...
    async def send_str(self, data: str) -> None: ...


type WebsocketMessage = (
    WebsocketClosedMessage | WebsocketBytesMessage | WebsocketStrMessage
)


class WebsocketClosedMessage(Protocol):
    kind: Literal[0]
    data: None


class WebsocketBytesMessage(Protocol):
    kind: Literal[1]
    data: bytes


class WebsocketStrMessage(Protocol):
    kind: Literal[2]
    data: str
