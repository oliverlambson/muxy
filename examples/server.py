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
import sqlite3
from json.decoder import JSONDecodeError

from granian.server.embed import Server

from muxy.router import Router, path_params
from muxy.rsgi import (
    HTTPProtocol,
    RSGIHTTPHandler,
    Scope,
)

ADDRESS = "127.0.0.1"
PORT = 8000

db = sqlite3.connect(":memory:")
db.cursor().executescript("""
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
""")


async def main() -> None:
    router = Router()
    router.get("/user/{id}", get_user(db))
    router.post("/user", create_user(db))
    router.patch("/user/{id}", update_user(db))

    server = Server(router)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


def get_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    cur = db.cursor()

    async def handler(s: Scope, p: HTTPProtocol) -> None:
        user_id = path_params.get()["id"]
        cur.execute("SELECT * FROM user WHERE id = ?", user_id)
        result = cur.fetchone()
        if result is None:
            p.response_empty(404, [])
            return
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(200, [], serialized)

    return handler


def create_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    cur = db.cursor()

    async def handler(s: Scope, p: HTTPProtocol) -> None:
        body = await p()
        try:
            payload = json.loads(body)
        except JSONDecodeError:
            p.response_empty(422, [])
            return
        try:
            name = payload["name"]
        except KeyError:
            p.response_empty(422, [])
            return
        cur.execute("INSERT INTO user (name) VALUES (?) RETURNING *", (name,))
        result = cur.fetchone()
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [], serialized)

    return handler


def update_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    cur = db.cursor()

    async def handler(s: Scope, p: HTTPProtocol) -> None:
        user_id = path_params.get()["id"]
        body = await p()
        try:
            payload = json.loads(body)
        except JSONDecodeError:
            p.response_empty(422, [])
            return
        try:
            name = payload["name"]
        except KeyError:
            p.response_empty(422, [])
            return
        cur.execute(
            "UPDATE user SET name = ? WHERE id = ? RETURNING *", (name, user_id)
        )
        result = cur.fetchone()
        if result is None:
            p.response_empty(422, [])
            return
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [], serialized)

    return handler


if __name__ == "__main__":
    asyncio.run(main())
