# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy @ file:///${PROJECT_ROOT}/../muxy",
#     "granian[uvloop]>=2.6.0,<3.0.0",
# ]
# ///
"""RSGI server demo.

Fully functional web server using Granian + muxy Router.
"""

import asyncio
import json
import logging
import sqlite3
from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from functools import wraps
from typing import Any

from granian.server.embed import Server

from muxy import Router, path_params
from muxy.rsgi import HTTPProtocol, HTTPScope

ADDRESS = "127.0.0.1"
PORT = 8000

_db = sqlite3.connect(":memory:")
_db.cursor().executescript("""
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
""")


db_var = ContextVar("db_var")


def with_db[T, **P](
    f: Callable[P, Coroutine[Any, Any, T]],
) -> Callable[P, Coroutine[Any, Any, T]]:
    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with db_var.set(_db):
            return await f(*args, **kwargs)

    return wrapper


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    router.finalize()
    server = Server(router, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


router = Router()


async def not_found(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("Content-Type", "text/plain")], "Not found")


router.not_found(not_found)


async def method_not_allowed(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(405, [("Content-Type", "text/plain")], "Method not allowed")


router.method_not_allowed(method_not_allowed)


async def home(s: HTTPScope, p: HTTPProtocol) -> None:
    p.response_str(200, [("Content-Type", "text/plain")], "Welcome home")


router.get("/", home)


@with_db
async def get_user(s: HTTPScope, p: HTTPProtocol) -> None:
    db = db_var.get()
    cur = db.cursor()
    user_id = path_params.get()["id"]
    try:
        user_id = int(user_id)
    except ValueError:
        p.response_str(404, [("Content-Type", "text/plain")], "Not found")
        return
    cur.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    result = cur.fetchone()
    if result is None:
        p.response_str(404, [("Content-Type", "text/plain")], "Not found")
        return
    serialized = json.dumps({"id": result[0], "name": result[1]})
    p.response_str(200, [("Content-Type", "application/json")], serialized)


router.get("/user/{id}", get_user)
if __name__ == "__main__":
    asyncio.run(main())
