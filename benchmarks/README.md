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

Server: [Granian](https://github.com/emmett-framework/granian) with uvloop, 1 worker.

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

|               | Requests/sec   | Latency p50   | Latency p99   |
| ------------- | -------------- | ------------- | ------------- |
| **muxy**      | 176,679 (100%) | 0.51ms (100%) | 0.71ms (100%) |
| **starlette** | 50,995 (29%)   | 1.87ms (367%) | 2.35ms (331%) |
| **litestar**  | 52,530 (30%)   | 1.90ms (373%) | 2.09ms (294%) |
| **fastapi**   | 30,325 (17%)   | 3.01ms (590%) | 3.94ms (555%) |

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

- muxy: 179,251, 176,679, 176,166
- starlette: 50,995, 51,120, 50,967
- litestar: 53,756, 51,995, 52,530
- fastapi: 29,916, 30,325, 30,445

</details>
