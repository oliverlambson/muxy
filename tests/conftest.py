from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from muxy.rsgi import HTTPScope


@dataclass
class MockHTTPScope:
    proto: Literal["http"] = "http"
    http_version: Literal["1", "1.1", "2"] = "1.1"
    rsgi_version: str = "1.0"
    server: str = "localhost"
    client: str = "127.0.0.1"
    scheme: str = "http"
    method: str = "GET"
    path: str = "/"
    query_string: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)
    authority: str | None = None


class MockHTTPStreamTransport:
    """Mock stream transport that captures sent data."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    async def send_bytes(self, data: bytes) -> None:
        self.chunks.append(data)

    async def send_str(self, data: str) -> None:
        self.chunks.append(data.encode("utf-8"))

    def get_data(self) -> bytes:
        return b"".join(self.chunks)


class MockHTTPProtocol:
    """Mock protocol that captures response data."""

    def __init__(self) -> None:
        self.response_status: int | None = None
        self.response_headers: list[tuple[str, str]] | None = None
        self.response_body: bytes | None = None
        self.stream_transport: MockHTTPStreamTransport | None = None

    async def __call__(self) -> bytes:
        raise NotImplementedError

    def __aiter__(self) -> bytes:
        raise NotImplementedError

    async def client_disconnect(self) -> None:
        raise NotImplementedError

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None:
        self.response_status = status
        self.response_headers = headers
        self.response_body = b""

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        self.response_status = status
        self.response_headers = headers
        self.response_body = body.encode("utf-8")

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        self.response_status = status
        self.response_headers = headers
        self.response_body = body

    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None:
        raise NotImplementedError

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        raise NotImplementedError

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> MockHTTPStreamTransport:
        self.response_status = status
        self.response_headers = headers
        self.stream_transport = MockHTTPStreamTransport()
        return self.stream_transport


def mock_scope(
    path: str = "/",
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> HTTPScope:
    return MockHTTPScope(path=path, method=method, headers=headers or {})
