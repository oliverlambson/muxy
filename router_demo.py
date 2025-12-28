"""Zero dependency router implementation with path param support.

Heavily inspired by go 1.22+ net/http's ServeMux
"""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from rsgisrv.router import Router, path_params
from rsgisrv.rsgi.proto import (
    HTTPProtocol,
    HTTPScope,
    HTTPStreamTransport,
    Scope,
)


# handlers
async def admin_home_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> admin home")


async def admin_user_rename_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"> admin user {path_params.get()['id']} rename")


async def admin_user_transaction_view_handler(s: Scope, p: HTTPProtocol) -> None:
    print(
        f"> admin user {path_params.get()['id']} transaction {path_params.get()['tx']}"
    )


async def static_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"> static {path_params.get()['path']}")


async def home_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> home")


# not found handlers
async def not_found_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> 404")


async def admin_not_found_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> admin 404")


# method not allowed handlers
async def method_not_allowed_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> 405")


async def static_method_not_allowed_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> static 405")


# middleware
def admin_middleware[T](f: T) -> T:
    print(">> admin middleware")
    return f


def admin_user_middleware[T](f: T) -> T:
    print(">> admin user middleware")
    return f


def admin_user_rename_middleware[T](f: T) -> T:
    print(">> admin user rename middleware")
    return f


"""
handlers:
POST    /admin/user/{id}/rename             admin_user_rename_handler
GET     /admin/user/{id}/transaction/{tx}   admin_user_transaction_view_handler
GET     /admin                              admin_home_handler
GET     /static/{path...}                   static_handler
<any>   /                                   home_handler

not found handlers:
<fallback>  not_found_handler
/admin      admin_not_found_handler

method not allowed handlers:
<fallback>  method_not_allowed_handler
/static     static_method_not_allowed_handler

middleware:
/admin                          admin_middleware
/admin/user                     admin_user_middleware
POST /admin/user/{id}/rename    admin_user_rename_middleware
"""


@dataclass
class TestHttpScope:
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


def _test_scope(path: str, method: str) -> HTTPScope:
    return TestHttpScope(
        proto="http",
        http_version="1.1",
        rsgi_version="",
        server="",
        client="",
        scheme="",
        method=method,
        path=path,
        query_string="",
        headers={},
        authority=None,
    )


class TestHTTPProto:
    async def __call__(self) -> bytes:
        raise NotImplementedError

    def __aiter__(self) -> bytes:
        raise NotImplementedError

    async def client_disconnect(self) -> None:
        raise NotImplementedError

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None:
        raise NotImplementedError

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        raise NotImplementedError

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        raise NotImplementedError

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
    ) -> HTTPStreamTransport:
        raise NotImplementedError


_test_proto = TestHTTPProto()


async def _test_user_id_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"hi user {path_params.get()['id']}")


async def _test_user_profile_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"user profile: {path_params.get()['id']}")


async def main() -> None:
    # test router
    router = Router()
    router.get("/user/{id}", _test_user_id_handler)
    router.get("/user/{id}/profile", _test_user_profile_handler)
    await router.__rsgi__(_test_scope("/user/42", "GET"), _test_proto)
    await router.__rsgi__(_test_scope("/user/42/profile", "GET"), _test_proto)


if __name__ == "__main__":
    asyncio.run(main())
