#!/bin/bash
# Benchmark runner for muxy vs starlette
# Usage: ./scripts/bench.sh
# Environment variables:
#   DURATION - test duration in seconds (default: 10)
#   CONNECTIONS - concurrent connections (default: 100)
#   THREADS - wrk threads (default: 4)
#   RUNS - number of runs per framework (default: 3)

set -e

# Configuration
DURATION=${DURATION:-10}
CONNECTIONS=${CONNECTIONS:-100}
THREADS=${THREADS:-4}
RUNS=${RUNS:-3}
WARMUP_DURATION=3
PORT=8080

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[bench]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[bench]${NC} $1"
}

error() {
    echo -e "${RED}[bench]${NC} $1"
}

check_deps() {
    if ! command -v wrk &>/dev/null; then
        error "wrk not found. Install with: brew install wrk"
        exit 1
    fi
    if ! command -v uv &>/dev/null; then
        error "uv not found. Install from: https://github.com/astral-sh/uv"
        exit 1
    fi
}

get_system_info() {
    local os=$(uname -s)
    local arch=$(uname -m)

    if [ "$os" = "Darwin" ]; then
        DEVICE=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Model Name" | cut -d: -f2 | xargs)
        CPU=$(sysctl -n machdep.cpu.brand_string)
        CORES=$(sysctl -n hw.ncpu)
        MEMORY_GB=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
    else
        DEVICE=$(cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || hostname)
        CPU=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs)
        CORES=$(nproc)
        MEMORY_GB=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024))
    fi

    OS_INFO="${os} $(uname -r) (${arch})"
}

generate_targets() {
    log "Generating targets..."
    uv run python -m benchmarks.runner.targets >scripts/targets.txt
    local count=$(wc -l <scripts/targets.txt | tr -d ' ')
    log "Generated $count targets"
}

start_server() {
    local framework=$1
    local interface=$2

    if lsof -i :$PORT >/dev/null 2>&1; then
        error "Port $PORT is already in use! Aborting."
        lsof -i :$PORT
        exit 1
    fi

    log "Starting $framework server..."

    if [ "$framework" = "sanic" ]; then
        # sanic uses its own server
        uv run sanic "benchmarks.app.sanic:root_router" \
            --port $PORT \
            --single-process \
            >/dev/null 2>&1 &
    else
        uv run granian "benchmarks.app.${framework}:root_router" \
            --loop uvloop \
            --interface "$interface" \
            --port $PORT \
            --workers 1 \
            >/dev/null 2>&1 &
    fi

    SERVER_PID=$!

    # wait for server to be ready
    local max_wait=3
    local waited=0
    while ! curl -s "http://localhost:$PORT/" >/dev/null 2>&1; do
        sleep 0.1
        waited=$((waited + 1))
        if [ $waited -gt $((max_wait * 10)) ]; then
            error "Server failed to start within ${max_wait}s"
            kill $SERVER_PID 2>/dev/null || true
            exit 1
        fi
    done
    log "$framework server ready (PID: $SERVER_PID)"
}

stop_server() {
    if [ -n "$SERVER_PID" ]; then
        log "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
        SERVER_PID=""
        sleep 1 # ensure port is released before next server starts
    fi
}

warmup() {
    log "Warming up for ${WARMUP_DURATION}s..."
    wrk -t1 -c10 -d${WARMUP_DURATION}s -s scripts/routes.lua "http://localhost:$PORT" >/dev/null 2>&1
}

run_benchmark() {
    local framework=$1
    local run_num=$2
    local output_file=$3

    log "Run $run_num: wrk -t$THREADS -c$CONNECTIONS -d${DURATION}s"

    local output=$(wrk -t$THREADS -c$CONNECTIONS -d${DURATION}s -s scripts/routes.lua "http://localhost:$PORT" 2>&1)

    local json=$(echo "$output" | sed -n '/RESULTS_JSON_START/,/RESULTS_JSON_END/p' | grep -v 'RESULTS_JSON')

    if [ -z "$json" ]; then
        error "Failed to extract results from wrk output"
        echo "$output"
        return 1
    fi

    echo "$json" >>"$output_file"
}

benchmark_framework() {
    local framework=$1
    local interface=$2
    local results_file=$3

    log "=== Benchmarking $framework ==="

    start_server "$framework" "$interface"
    warmup

    echo "\"$framework\": [" >>"$results_file"

    for run in $(seq 1 $RUNS); do
        if [ $run -gt 1 ]; then
            echo "," >>"$results_file"
            sleep 1 # brief pause between runs
        fi
        run_benchmark "$framework" "$run" "$results_file"
    done

    echo "]" >>"$results_file"

    stop_server
}

main() {
    check_deps
    get_system_info
    generate_targets

    mkdir -p results
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local results_file="results/${timestamp}.json"
    local temp_file="results/${timestamp}_temp.json"

    log "Configuration: duration=${DURATION}s, connections=$CONNECTIONS, threads=$THREADS, runs=$RUNS"
    log "System: $DEVICE / $CPU ($CORES cores, ${MEMORY_GB}GB RAM)"
    log "Results will be saved to: $results_file"

    # start json file
    cat >"$temp_file" <<EOF
{
  "metadata": {
    "timestamp": "$(date -Iseconds)",
    "duration_sec": $DURATION,
    "connections": $CONNECTIONS,
    "threads": $THREADS,
    "runs": $RUNS,
    "system": {
      "device": "$DEVICE",
      "os": "$OS_INFO",
      "cpu": "$CPU",
      "cores": $CORES,
      "memory_gb": $MEMORY_GB
    }
  },
  "results": {
EOF

    benchmark_framework "fastapi" "asgi" "$temp_file"
    echo "," >>"$temp_file"
    benchmark_framework "litestar" "asgi" "$temp_file"
    echo "," >>"$temp_file"
    benchmark_framework "quart" "asgi" "$temp_file"
    echo "," >>"$temp_file"
    benchmark_framework "sanic" "sanic" "$temp_file"
    echo "," >>"$temp_file"
    benchmark_framework "starlette" "asgi" "$temp_file"
    echo "," >>"$temp_file"
    benchmark_framework "muxy" "rsgi" "$temp_file"

    # close json
    echo "  }" >>"$temp_file"
    echo "}" >>"$temp_file"

    jq -r '.' "$temp_file" >"$results_file"

    # copy to results.json (gets committed)
    cp "$results_file" results.json

    # create latest symlink for convenience
    ln -sf "${timestamp}.json" results/latest.json

    log "Results saved to: $results_file"
    log ""

    # print summary to terminal
    uv run python -m benchmarks.runner.summarize "$results_file"

    # update README.md with results
    log "Updating README.md..."
    uv run python -m benchmarks.runner.summarize "$results_file" --markdown >README.md.new
    if [ -f README.md ]; then
        # preserve everything before "## Results"
        sed '/^## Results/,$d' README.md >README.md.header
        cat README.md.header README.md.new >README.md
        rm README.md.header README.md.new
    else
        cat README.md.new >>README.md
        rm README.md.new
    fi

    log "README.md updated"
}

# cleanup on exit
trap stop_server EXIT

main
