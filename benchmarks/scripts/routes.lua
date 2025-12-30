-- wrk Lua script to cycle through all routes
-- Usage: wrk -t4 -c100 -d10s -s routes.lua http://localhost:8080

-- Load targets at script load time (shared across all contexts)
local targets = {}
local counter = 0

local file = io.open("scripts/targets.txt", "r")
if not file then
    print("ERROR: Could not open scripts/targets.txt")
    print("Generate it with: uv run python -m benchmarks.runner.targets > scripts/targets.txt")
    os.exit(1)
end

for line in file:lines() do
    local method, path = line:match("^(%S+)%s+(.+)$")
    if method and path then
        table.insert(targets, {method = method, path = path})
    end
end
file:close()

if #targets == 0 then
    print("ERROR: No targets loaded from scripts/targets.txt")
    os.exit(1)
end

print(string.format("Loaded %d targets", #targets))

-- Cycle through targets on each request
function request()
    counter = counter + 1
    local idx = ((counter - 1) % #targets) + 1
    local target = targets[idx]

    return wrk.format(target.method, target.path)
end

-- Report results at the end
function done(summary, latency, requests)
    local errors = summary.errors.connect + summary.errors.read +
                   summary.errors.write + summary.errors.status + summary.errors.timeout

    -- Output JSON-formatted results for parsing
    print(string.format("\n--- RESULTS_JSON_START ---"))
    print(string.format("{"))
    print(string.format('  "requests": %d,', summary.requests))
    print(string.format('  "duration_sec": %.2f,', summary.duration / 1000000))
    print(string.format('  "rps": %.2f,', summary.requests / (summary.duration / 1000000)))
    print(string.format('  "latency_mean_ms": %.2f,', latency.mean / 1000))
    print(string.format('  "latency_stdev_ms": %.2f,', latency.stdev / 1000))
    print(string.format('  "latency_max_ms": %.2f,', latency.max / 1000))
    print(string.format('  "latency_p50_ms": %.2f,', latency:percentile(50) / 1000))
    print(string.format('  "latency_p90_ms": %.2f,', latency:percentile(90) / 1000))
    print(string.format('  "latency_p99_ms": %.2f,', latency:percentile(99) / 1000))
    print(string.format('  "errors": %d,', errors))
    print(string.format('  "targets_count": %d', #targets))
    print(string.format("}"))
    print(string.format("--- RESULTS_JSON_END ---"))
end
