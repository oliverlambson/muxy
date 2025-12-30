"""Summarize benchmark results and print comparison table."""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

FRAMEWORKS = ["muxy", "starlette", "fastapi"]
BASELINE = "muxy"


def load_results(path: Path) -> dict:
    """Load benchmark results from JSON file."""
    with open(path) as f:
        return json.load(f)


def get_median(runs: list[dict], key: str) -> float:
    """Get median value for a metric across runs."""
    values = [run[key] for run in runs]
    return statistics.median(values)


def format_delta(
    baseline_val: float, compare_val: float, *, lower_is_better: bool = False
) -> str:
    """Format delta as percentage with +/- sign (comparing against baseline)."""
    if baseline_val == 0:
        return "N/A"

    # For "lower is better" metrics, flip the comparison
    if lower_is_better:
        delta = ((baseline_val - compare_val) / baseline_val) * 100
    else:
        delta = ((compare_val - baseline_val) / baseline_val) * 100

    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f}%"


def extract_stats(results: dict) -> dict:
    """Extract statistics from results."""
    metadata = results["metadata"]
    stats = {"metadata": metadata, "frameworks": {}}

    for fw in FRAMEWORKS:
        if fw not in results["results"]:
            continue
        runs = results["results"][fw]
        stats["frameworks"][fw] = {
            "rps": get_median(runs, "rps"),
            "p50": get_median(runs, "latency_p50_ms"),
            "p99": get_median(runs, "latency_p99_ms"),
            "requests": int(get_median(runs, "requests")),
            "runs": runs,
            "errors": sum(r["errors"] for r in runs),
        }

    # Get targets count from first available framework
    first_fw = next(iter(stats["frameworks"]))
    stats["targets_count"] = results["results"][first_fw][0]["targets_count"]

    return stats


def print_terminal(stats: dict) -> None:
    """Print formatted comparison summary to terminal."""
    metadata = stats["metadata"]
    frameworks = stats["frameworks"]
    system = metadata["system"]
    baseline = frameworks[BASELINE]

    print()
    print("=" * 80)
    print("  muxy vs starlette vs fastapi benchmark results")
    print("=" * 80)
    print()

    date = datetime.fromisoformat(metadata["timestamp"]).date()
    print(f"  Date:   {date}")
    print(f"  Device: {system['device']}")
    print(f"  CPU:    {system['cpu']}")
    print(f"          {system['cores']} cores, {system['memory_gb']}GB RAM")
    print()

    print(f"  Routes exercised: {stats['targets_count']}")
    print(f"  Duration: {metadata['duration_sec']}s x {metadata['runs']} runs")
    print(f"  Connections: {metadata['connections']}, Threads: {metadata['threads']}")
    print()

    print("-" * 80)
    header = f"  {'Metric':<17}"
    for fw in FRAMEWORKS:
        if fw in frameworks:
            header += f" {fw:>12}"
    header += " {'vs starlette':>14} {'vs fastapi':>12}"
    print(
        f"  {'Metric':<17} {'muxy':>12} {'starlette':>12} {'fastapi':>12} {'vs star':>10} {'vs fast':>10}"
    )
    print("-" * 80)

    # RPS row
    rps_vals = [
        f"{frameworks[fw]['rps']:>12,.0f}" for fw in FRAMEWORKS if fw in frameworks
    ]
    star_delta = format_delta(baseline["rps"], frameworks["starlette"]["rps"])
    fast_delta = format_delta(baseline["rps"], frameworks["fastapi"]["rps"])
    print(
        f"  {'Requests/sec':<17} {' '.join(rps_vals)} {star_delta:>10} {fast_delta:>10}"
    )

    # p50 row
    p50_vals = [
        f"{frameworks[fw]['p50']:>12,.2f}" for fw in FRAMEWORKS if fw in frameworks
    ]
    star_delta = format_delta(
        baseline["p50"], frameworks["starlette"]["p50"], lower_is_better=True
    )
    fast_delta = format_delta(
        baseline["p50"], frameworks["fastapi"]["p50"], lower_is_better=True
    )
    print(
        f"  {'Latency p50 (ms)':<17} {' '.join(p50_vals)} {star_delta:>10} {fast_delta:>10}"
    )

    # p99 row
    p99_vals = [
        f"{frameworks[fw]['p99']:>12,.2f}" for fw in FRAMEWORKS if fw in frameworks
    ]
    star_delta = format_delta(
        baseline["p99"], frameworks["starlette"]["p99"], lower_is_better=True
    )
    fast_delta = format_delta(
        baseline["p99"], frameworks["fastapi"]["p99"], lower_is_better=True
    )
    print(
        f"  {'Latency p99 (ms)':<17} {' '.join(p99_vals)} {star_delta:>10} {fast_delta:>10}"
    )

    # Total requests row
    req_vals = [
        f"{frameworks[fw]['requests']:>12,}" for fw in FRAMEWORKS if fw in frameworks
    ]
    print(f"  {'Total requests':<17} {' '.join(req_vals)}")

    print("-" * 80)

    print()
    print("  Individual runs (rps):")
    for fw in FRAMEWORKS:
        if fw in frameworks:
            runs_str = ", ".join(f"{r['rps']:,.0f}" for r in frameworks[fw]["runs"])
            print(f"    {fw}: {runs_str}")

    total_errors = sum(
        frameworks[fw]["errors"] for fw in FRAMEWORKS if fw in frameworks
    )
    if total_errors > 0:
        print()
        errors_str = ", ".join(
            f"{fw}={frameworks[fw]['errors']}" for fw in FRAMEWORKS if fw in frameworks
        )
        print(f"  Errors: {errors_str}")

    print()


def format_markdown(stats: dict) -> str:
    """Format results as markdown."""
    metadata = stats["metadata"]
    frameworks = stats["frameworks"]
    system = metadata["system"]
    baseline = frameworks[BASELINE]

    star_rps_delta = format_delta(baseline["rps"], frameworks["starlette"]["rps"])
    fast_rps_delta = format_delta(baseline["rps"], frameworks["fastapi"]["rps"])
    star_p50_delta = format_delta(
        baseline["p50"], frameworks["starlette"]["p50"], lower_is_better=True
    )
    fast_p50_delta = format_delta(
        baseline["p50"], frameworks["fastapi"]["p50"], lower_is_better=True
    )
    star_p99_delta = format_delta(
        baseline["p99"], frameworks["starlette"]["p99"], lower_is_better=True
    )
    fast_p99_delta = format_delta(
        baseline["p99"], frameworks["fastapi"]["p99"], lower_is_better=True
    )

    muxy = frameworks["muxy"]
    starlette = frameworks["starlette"]
    fastapi = frameworks["fastapi"]

    lines = [
        "## Results",
        "",
        "| Metric       | muxy    | starlette | fastapi | vs starlette | vs fastapi |",
        "| ------------ | ------- | --------- | ------- | ------------ | ---------- |",
        f"| Requests/sec | {muxy['rps']:,.0f} | {starlette['rps']:,.0f} | {fastapi['rps']:,.0f} | {star_rps_delta} | {fast_rps_delta} |",
        f"| Latency p50  | {muxy['p50']:.2f}ms | {starlette['p50']:.2f}ms | {fastapi['p50']:.2f}ms | {star_p50_delta} | {fast_p50_delta} |",
        f"| Latency p99  | {muxy['p99']:.2f}ms | {starlette['p99']:.2f}ms | {fastapi['p99']:.2f}ms | {star_p99_delta} | {fast_p99_delta} |",
        "",
        "<details>",
        "<summary>Benchmark details</summary>",
        "",
    ]

    date = datetime.fromisoformat(metadata["timestamp"]).date()
    lines.extend([f"**Date**: {date}", ""])

    device = system["device"]
    cpu = system["cpu"]
    cores = system["cores"]
    memory = system["memory_gb"]
    lines.extend(
        [
            f"**Device**: {device}",
            f"**CPU**: {cpu} ({cores} cores, {memory}GB RAM)",
            "",
        ]
    )

    lines.extend(
        [
            f"- **Routes exercised**: {stats['targets_count']}",
            f"- **Duration**: {metadata['duration_sec']}s x {metadata['runs']} runs",
            f"- **Connections**: {metadata['connections']}",
            f"- **wrk threads**: {metadata['threads']}",
            "",
            "Individual runs (requests/sec):",
            "",
        ]
    )

    for fw in FRAMEWORKS:
        if fw in frameworks:
            runs_str = ", ".join(f"{r['rps']:,.0f}" for r in frameworks[fw]["runs"])
            lines.append(f"- {fw}: {runs_str}")

    lines.extend(["", "</details>", ""])

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m benchmarks.runner.summarize <results.json> [--markdown]"
        )
        sys.exit(1)

    results_path = Path(sys.argv[1])
    markdown_mode = "--markdown" in sys.argv

    if not results_path.exists():
        print(f"Error: File not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    results = load_results(results_path)
    stats = extract_stats(results)

    if markdown_mode:
        print(format_markdown(stats))
    else:
        print_terminal(stats)


if __name__ == "__main__":
    main()
