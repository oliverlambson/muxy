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
| **muxy**       | 172,908 (100%) |  0.53ms (100%) | 0.73ms (100%) |
| **muxy_asgi**  |  158,862 (92%) |  0.57ms (108%) | 0.79ms (108%) |
| **sanic**      |   65,546 (38%) |  1.54ms (291%) | 1.73ms (237%) |
| **blacksheep** |   51,763 (30%) |  2.01ms (379%) | 2.18ms (299%) |
| **litestar**   |   51,313 (30%) |  1.95ms (368%) | 2.14ms (293%) |
| **starlette**  |   51,171 (30%) |  1.86ms (351%) | 2.33ms (319%) |
| **fastapi**    |   30,185 (17%) |  3.06ms (577%) | 3.97ms (544%) |
| **quart**      |   17,984 (10%) | 5.57ms (1051%) | 6.44ms (882%) |

<details>
<summary>Benchmark details</summary>

**Date**: 2025-12-31

**Device**: MacBook Air
**CPU**: Apple M3 (8 cores, 16GB RAM)

- **Routes exercised**: 23046
- **Duration**: 10s x 3 runs
- **Connections**: 100
- **wrk threads**: 4

Individual runs (requests/sec):

- muxy: 172,107, 172,908, 173,421
- muxy_asgi: 162,577, 146,567, 158,862
- sanic: 64,539, 65,546, 66,762
- blacksheep: 51,763, 51,764, 51,699
- litestar: 51,313, 51,312, 52,508
- starlette: 51,171, 51,232, 51,163
- fastapi: 30,153, 30,185, 30,224
- quart: 17,984, 18,017, 17,970

</details>
