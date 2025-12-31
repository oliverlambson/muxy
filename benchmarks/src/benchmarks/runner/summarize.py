"""Summarize benchmark results and print comparison table."""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

FRAMEWORKS = [
    "muxy",
    "starlette",
    "litestar",
    "sanic",
    "fastapi",
    "quart",
    "blacksheep",
]
BASELINE = "muxy"


def load_results(path: Path) -> dict:
    """Load benchmark results from JSON file."""
    with open(path) as f:
        return json.load(f)


def get_median(runs: list[dict], key: str) -> float:
    """Get median value for a metric across runs."""
    values = [run[key] for run in runs]
    return statistics.median(values)


def format_relative(baseline_val: float, compare_val: float) -> str:
    """Format value as percentage relative to baseline."""
    if baseline_val == 0:
        return "N/A"
    pct = (compare_val / baseline_val) * 100
    return f"{pct:.0f}%"


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
    print("=" * 70)
    print("  Benchmark Results")
    print("=" * 70)
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

    print("-" * 70)
    print(f"  {'':<12} {'Requests/sec':>17} {'Latency p50':>17} {'Latency p99':>17}")
    print("-" * 70)

    for fw in FRAMEWORKS:
        if fw not in frameworks:
            continue
        data = frameworks[fw]
        rps_pct = format_relative(baseline["rps"], data["rps"])
        p50_pct = format_relative(baseline["p50"], data["p50"])
        p99_pct = format_relative(baseline["p99"], data["p99"])

        rps_str = f"{data['rps']:,.0f} ({rps_pct})"
        p50_str = f"{data['p50']:.2f}ms ({p50_pct})"
        p99_str = f"{data['p99']:.2f}ms ({p99_pct})"

        print(f"  {fw:<12} {rps_str:>17} {p50_str:>17} {p99_str:>17}")

    print("-" * 70)

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

    lines = [
        "## Results",
        "",
        "|     | Requests/sec | Latency p50 | Latency p99 |",
        "| --- | ------------ | ----------- | ----------- |",
    ]

    for fw in FRAMEWORKS:
        if fw not in frameworks:
            continue
        data = frameworks[fw]
        rps_pct = format_relative(baseline["rps"], data["rps"])
        p50_pct = format_relative(baseline["p50"], data["p50"])
        p99_pct = format_relative(baseline["p99"], data["p99"])

        lines.append(
            f"| **{fw}** | {data['rps']:,.0f} ({rps_pct}) | "
            f"{data['p50']:.2f}ms ({p50_pct}) | {data['p99']:.2f}ms ({p99_pct}) |"
        )

    lines.extend(
        [
            "",
            "<details>",
            "<summary>Benchmark details</summary>",
            "",
        ]
    )

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
