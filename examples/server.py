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
from json.decoder import JSONDecodeError

from granian.server.embed import Server

from muxy import Router, path_params
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler

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
    logging.basicConfig(level=logging.INFO)

    router = Router()
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.get("/", home)
    router.mount("/user", user_router(_db))
    router.mount("/product", product_router(_db))
    router.finalize()

    server = Server(router, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


async def not_found(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("Content-Type", "text/plain")], "Not found")


async def method_not_allowed(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("Content-Type", "text/plain")], "Method not allowed")


async def home(s: HTTPScope, p: HTTPProtocol) -> None:
    p.response_str(200, [("Content-Type", "text/plain")], "Welcome home")


def user_router(db: sqlite3.Connection) -> Router:
    router = Router()
    router.get("/", get_users(db))
    router.get("/{id}", get_user(db))
    router.post("/", create_user(db))
    router.patch("/{id}", update_user(db))
    return router


# closure over handler to inject dependencies
def get_users(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        cur.execute("SELECT * FROM user")
        result = cur.fetchall()
        serialized = json.dumps([{"id": row[0], "name": row[1]} for row in result])
        p.response_str(200, [("Content-Type", "application/json")], serialized)

    return handler


def get_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
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

    return handler


def create_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        body = await p()
        try:
            payload = json.loads(body)
        except JSONDecodeError:
            p.response_str(422, [("Content-Type", "text/plain")], "Invalid json")
            return
        try:
            name = payload["name"]
        except KeyError:
            p.response_str(422, [("Content-Type", "text/plain")], "Missing name")
            return
        cur.execute("INSERT INTO user (name) VALUES (?) RETURNING *", (name,))
        result = cur.fetchone()
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [("Content-Type", "application/json")], serialized)

    return handler


def update_user(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        user_id = path_params.get()["id"]
        body = await p()
        try:
            payload = json.loads(body)
        except JSONDecodeError:
            p.response_str(422, [("Content-Type", "text/plain")], "Invalid json")
            return
        try:
            name = payload["name"]
        except KeyError:
            p.response_str(422, [("Content-Type", "text/plain")], "Missing name")
            return
        cur.execute(
            "UPDATE user SET name = ? WHERE id = ? RETURNING *", (name, user_id)
        )
        result = cur.fetchone()
        if result is None:
            p.response_str(404, [("Content-Type", "text/plain")], "Not found")
            return
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [("Content-Type", "application/json")], serialized)

    return handler


def product_router(db: sqlite3.Connection) -> Router:
    router = Router()
    router.get("/", get_products(_db))
    router.post("/", create_product(_db))
    router.get("/{id}", get_product(_db))
    return router


def get_products(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        cur.execute("SELECT * FROM product")
        result = cur.fetchall()
        serialized = json.dumps([{"id": row[0], "name": row[1]} for row in result])
        p.response_str(200, [("Content-Type", "application/json")], serialized)

    return handler


def get_product(db: sqlite3.Connection) -> RSGIHTTPHandler:
    cur = db.cursor()

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        product_id = path_params.get()["id"]
        try:
            product_id = int(product_id)
        except ValueError:
            p.response_str(404, [("Content-Type", "text/plain")], "Not found")
            return
        cur.execute("SELECT * FROM product WHERE id = ?", (product_id,))
        result = cur.fetchone()
        if result is None:
            p.response_str(404, [("Content-Type", "text/plain")], "Not found")
            return
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(200, [("Content-Type", "application/json")], serialized)

    return handler


def create_product(db: sqlite3.Connection) -> RSGIHTTPHandler:
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        cur = db.cursor()
        body = await p()
        try:
            payload = json.loads(body)
        except JSONDecodeError:
            p.response_str(422, [("Content-Type", "text/plain")], "Invalid json")
            return
        try:
            name = payload["name"]
        except KeyError:
            p.response_str(422, [("Content-Type", "text/plain")], "Missing name")
            return
        cur.execute("INSERT INTO product (name) VALUES (?) RETURNING *", (name,))
        result = cur.fetchone()
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [("Content-Type", "application/json")], serialized)

    return handler


if __name__ == "__main__":
    asyncio.run(main())
