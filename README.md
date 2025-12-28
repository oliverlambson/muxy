# muxy

`muxy` is a lightweight router for building HTTP services conforming to
Granian's Rust Server Gateway Interface (RSGI). It intentionally avoids magic,
prioritising explicit and composable code.

```
uv add muxy
```

## Features

- __first-class router composition__ - modularise your code by nesting routers with no overhead
- __correct, efficient routing__ - explicit route heirarchy so behaviour is always predictable
- __lightweight__ - the core router is little more than a simple datastructure
- __control__ - control the full HTTP request/response cycle without digging through framework layers
- __middleware__ - apply common logic to path groups simply and clearly

## Inspiration

Go's `net/http` and `go-chi/chi` are inspirations for `muxy`. I wanted their simplicity
without having to switch language. You can think of the `RSGI` interface as the muxy
equivalent of the net/http `HandlerFunc` interface, and `muxy.Router` as an equivalent of
chi's `Mux`.
