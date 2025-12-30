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

| Metric       | muxy    | starlette | delta   |
| ------------ | ------- | --------- | ------- |
| Requests/sec | 173,907 | 50,626    | +243.5% |
| Latency p50  | 0.51ms  | 1.88ms    | -72.9%  |
| Latency p99  | 0.77ms  | 2.38ms    | -67.6%  |

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

- muxy: 173,907, 173,679, 174,817
- starlette: 50,626, 50,620, 50,633

</details>
