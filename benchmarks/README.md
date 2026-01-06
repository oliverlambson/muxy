# Benchmarks

**Aim:** Compare framework overhead for a mid-sized "mature" app.

## What's being measured

Framework and protocol overhead: routing, middleware dispatch, request/response handling,
along with performance gains switching from ASGI to RSGI. All handlers return a simple
plaintext string, and middlewares are no-ops: isolating framework performance from
application logic.

## Setup

The app is implemented in the idiomatic style for each framework/router, the app
structure contains:

- **70 route patterns** across 10 routers (root, auth, products, orders, cart, payments, api, admin, etc.)
- **23,046 concrete URLs** (parameterized routes expanded with IDs 1-100)
- **Middleware chains** at multiple levels (logging, CORS, auth, rate limiting, etc.)
- **Nested routers** up to 4 levels deep (`/admin/users/{id}/activity`)

| Route type    | Examples                                              |
| ------------- | ----------------------------------------------------- |
| Static        | `/`, `/about`, `/api/v1/health`                       |
| Parameterized | `/products/{id}`, `/orders/{id}/invoice`              |
| Catch-all     | `/static/{path...}`                                   |
| Nested        | `/admin/users/{id}/activity`, `/api/v1/products/{id}` |

Servers:

- RSGI frameworks use [Granian](https://github.com/emmett-framework/granian) with uvloop, 1 worker.
- ASGI frameworks use [Granian](https://github.com/emmett-framework/granian) with uvloop, 1 worker.
- [Sanic](https://sanic.dev/en/) provides it's own server, so that's used instead for Sanic only.

## Running

The benchmark script uses [`wrk`](https://github.com/wg/wrk) to actually run the
stress-test. There's a prep script to generate the concrete URL inputs, and another
script to pretty-print the JSON results.

```bash
# install wrk
brew install wrk  # or whatever your package manager is

# run benchmarks
./scripts/bench.sh

# [optional] run benchmarks with custom parameters
DURATION=30 CONNECTIONS=200 RUNS=5 ./scripts/bench.sh
```

## Results

|                |   Requests/sec |    Latency p50 |   Latency p99 |
| -------------- | -------------: | -------------: | ------------: |
| **muxy**       | 174,693 (100%) |  0.52ms (100%) | 0.73ms (100%) |
| **muxy_asgi**  |  160,639 (92%) |  0.56ms (108%) | 0.84ms (115%) |
| **emmett55**   |   96,498 (55%) |  1.03ms (198%) | 1.22ms (167%) |
| **sanic**      |   65,586 (38%) |  1.54ms (296%) | 1.73ms (237%) |
| **blacksheep** |   51,650 (30%) |  2.01ms (387%) | 2.20ms (301%) |
| **litestar**   |   51,953 (30%) |  1.91ms (367%) | 2.16ms (296%) |
| **starlette**  |   50,472 (29%) |  1.90ms (365%) | 2.37ms (325%) |
| **fastapi**    |   30,212 (17%) |  3.05ms (587%) | 3.96ms (542%) |
| **quart**      |   17,724 (10%) | 5.65ms (1087%) | 6.63ms (908%) |

<details>
<summary>Benchmark details</summary>

**Date**: 2026-01-06

**Device**: MacBook Air
**CPU**: Apple M3 (8 cores, 16GB RAM)

- **Routes exercised**: 23046
- **Duration**: 10s x 3 runs
- **Connections**: 100
- **wrk threads**: 4

Individual runs (requests/sec):

- muxy: 175,690, 170,414, 174,693
- muxy_asgi: 162,571, 160,639, 159,804
- emmett55: 96,673, 96,498, 95,323
- sanic: 64,770, 65,888, 65,586
- blacksheep: 51,641, 51,650, 51,886
- litestar: 51,383, 52,775, 51,953
- starlette: 50,485, 50,148, 50,472
- fastapi: 30,252, 30,171, 30,212
- quart: 17,695, 17,724, 17,756

</details>
