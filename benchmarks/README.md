# Benchmarks

Comparing **muxy** (RSGI) vs **starlette** (ASGI) framework overhead.

## What's being measured

Framework and protocol overhead: routing, middleware dispatch, request/response handling,
along with performance gains switching from ASGI to RSGI. All handlers return a simple
plaintext string, and middlewares are no-ops isolating framework performance from
application logic.

## Setup

Both frameworks run identical applications with:

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

```bash
# Install wrk
brew install wrk

# Run benchmarks
./scripts/bench.sh

# Custom parameters
DURATION=30 CONNECTIONS=200 RUNS=5 ./scripts/bench.sh
```

## Results

| Metric       | muxy    | starlette | delta   |
| ------------ | ------- | --------- | ------- |
| Requests/sec | 174,051 | 51,016    | +241.2% |
| Latency p50  | 0.52ms  | 1.88ms    | -72.3%  |
| Latency p99  | 0.76ms  | 2.37ms    | -67.9%  |

<details>
<summary>Benchmark details</summary>

**Date**: 2025-12-30

**Device**: MacBook Air
**CPU**: Apple M3 (8 cores, 16GB RAM)

- **Routes exercised**: 23046
- **Duration**: 10s x 3 runs
- **Connections**: 100
- **wrk threads**: 4

Individual runs (requests/sec):

- muxy: 173,648, 175,475, 174,051
- starlette: 51,066, 51,016, 50,933

</details>
