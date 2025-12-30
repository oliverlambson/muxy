# muxy

`muxy` is a lightweight router for building HTTP services conforming to
Granian's Rust Server Gateway Interface (RSGI). It intentionally avoids magic,
prioritising explicit and composable code.

```
uv add muxy
```

## Features

- **first-class router composition** - modularise your code by nesting routers with no overhead
- **correct, efficient routing** - explicit route heirarchy so behaviour is always predictable
- **lightweight** - the core router is little more than a simple datastructure and has no dependencies
- **control** - control the full HTTP request/response cycle without digging through framework layers
- **middleware** - apply common logic to path groups simply and clearly

## Inspiration

Go's `net/http` and `go-chi/chi` are inspirations for `muxy`. I wanted their simplicity
without having to switch language. You can think of the `RSGI` interface as the muxy
equivalent of the net/http `HandlerFunc` interface, and `muxy.Router` as an equivalent of
chi's `Mux`.

## Examples

**Getting started**

```python
import asyncio

from granian.server.embed import Server
from muxy import Router
from muxy.rsgi import HTTPProtocol, HTTPScope

async def home(s: HTTPScope, p: HTTPProtocol) -> None:
    p.response_str(200, [], "Hello world!")

async def main() -> None:
    router = Router()
    router.get("/", home)

    server = Server(router)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

**Bigger app**

See [examples/server.py](https://github.com/oliverlambson/muxy/blob/main/examples/server.py) for a runnable script.

```python
import asyncio
import json
import sqlite3
from json.decoder import JSONDecodeError

from granian.server.embed import Server

from muxy import Router, path_params
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler


async def main() -> None:
    db = sqlite3.connect(":memory:")

    router = Router()
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.get("/", home)
    router.mount("/user", user_router(db))
    router.finalize()

    server = Server(router)
    await server.serve()


async def not_found(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("Content-Type", "text/plain")], "Not found")

async def method_not_allowed(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(405, [("Content-Type", "text/plain")], "Method not allowed")

async def home(s: HTTPScope, p: HTTPProtocol) -> None:
    p.response_str(200, [("Content-Type", "text/plain")], "Welcome home")


def user_router(db: sqlite3.Connection) -> Router:
    router = Router()
    router.get("/", get_users(db))
    router.get("/{id}", get_user(db))
    router.post("/", create_user(db))
    router.patch("/{id}", update_user(db))
    return router

def get_users(db: sqlite3.Connection) -> RSGIHTTPHandler:
    # closure over handler function to make db available within the handler
    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
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
            p.response_str(422, [("Content-Type", "text/plain")], "No name key")
            return
        cur.execute("INSERT INTO user (name) VALUES (?) RETURNING *", (name,))
        result = cur.fetchone()
        serialized = json.dumps({"id": result[0], "name": result[1]})
        p.response_str(201, [("Content-Type", "application/json")], serialized)

    return handler

def update_user(db: sqlite3.Connection) -> RSGIHTTPHandler: ...


if __name__ == "__main__":
    asyncio.run(main())
```
