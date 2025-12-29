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


async def main() -> None:
    router = Router()
    router.get("/user/{id}", get_user(_db))
    router.get("/user/", get_users(_db))
    router.post("/user/", create_user(_db))
    router.patch("/user/{id}", update_user(_db))

    product_router = Router()
    product_router.get("/", get_products(_db))
    product_router.post("/", create_product(_db))
    product_router.get("/{id}", get_product(_db))

    router.mount("/product", product_router)

    server = Server(router)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


# closure over handler to inject dependencies
def get_users(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        cur.execute("SELECT * FROM user")
        result = cur.fetchall()
        serialized = json.dumps([{"id": row[0], "name": row[1]} for row in result])
        p.response_str(200, [], serialized)

    return handler


def get_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
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
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
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
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
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


def get_products(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        cur.execute("SELECT * FROM product")
        result = cur.fetchall()
        serialized = json.dumps([{"id": row[0], "name": row[1]} for row in result])
        p.response_str(200, [], serialized)

    return handler


def get_product(db: sqlite3.Connection) -> RSGIHTTPHandler:
    cur = db.cursor()

    async def handler(s: Scope, p: HTTPProtocol) -> None:
        product_id = path_params.get()["id"]
        cur.execute("SELECT * FROM product WHERE id = ?", product_id)
        result = cur.fetchone()
        if result is None:
            p.response_empty(404, [])
            return
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(200, [], serialized)

    return handler


def create_product(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: Scope, p: HTTPProtocol) -> None:
        cur = db.cursor()
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
        cur.execute("INSERT INTO product (name) VALUES (?) RETURNING *", (name,))
        result = cur.fetchone()
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [], serialized)

    return handler


if __name__ == "__main__":
    asyncio.run(main())
