# rsgi-srv

A router/http request multiplexer for composing servers conforming to
Granian's Rust Server Gateway Interface (RSGI)

## Inspiration

<details>
    <summary>
Go's stdlib has a minimalist but fully-functional router that allows simple
composition of endpoint handlers. The routing uses a radix-tree which is far
more efficient than Starlette's linear search of regex patterns. Whether this
practically makes a difference, I don't really care, I just think it's a nice to
do things properly.
    </summary>

```go
package main

import (
	"fmt"
	"log"
	"net/http"
)

func helloWorld(w http.ResponseWriter, req *http.Request) { // implements `HandlerFunc` interface
	fmt.Print(w, "Hello world")
}

func main() {
    // i want a way to compose RSGI apps like this
	childMux := http.NewServeMux()                // implements `http.Handler` interface
	childMux.HandleFunc("GET /hello", helloWorld) // mount a `HandlerFunc`

	rootMux := http.NewServeMux()
	rootMux.Handle("/child/", http.StripPrefix("/child", childMux)) // nest an `http.Handler`

    // could then pass the root RSGI app to granian, which provides the `ListenAndServe`
	log.Fatal(http.ListenAndServe("localhost:8080", rootMux))
}
```

</details>

## Planning

<details>
    <summary>RSGI is our equivalent interface to `http.Handler`</summary>

```python
from asyncio import AbstractEventLoop
from typing import Protocol
from granian.rsgi import HTTPProtocol, Scope, WebsocketProtocol
class RSGI(Protocol):
    async def __rsgi__(
        self, __scope: Scope, __proto: HTTPProtocol | WebsocketProtocol
    ): ...
    def __rsgi_init__(self, __loop: AbstractEventLoop): ...
    def __rsgi_del__(self, __loop: AbstractEventLoop): ...
```

The request metadata & headers are in `Scope` and it's body is accessible in
`HTTPProtocol`. The response is writable using the `HTTPProtocol`.

Scope:

- `scheme`
- `method`
- `path`
- `query_string`
- `headers`
- `server`

Request body:

- `proto()`
- `async for chunk in proto()`

Response:

- `proto.response_empty(status, headers)`
- `proto.response_{str,bytes}(status, headers, body)`
- `proto.response_{file}(status, headers, path)`
- `proto.response_{stream}(status, headers).send_{str,bytes}(data)`

</details>

We need to implement a way to create and compose instances of applications
implementing the `RSGI`.
