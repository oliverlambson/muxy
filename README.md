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
- **lightweight** - the core router is little more than a simple datastructure
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
from muxy.router import Router
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
