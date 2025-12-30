"""Summarize benchmark results and print comparison table."""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path


def load_results(path: Path) -> dict:
    """Load benchmark results from JSON file."""
    with open(path) as f:
        return json.load(f)


def get_median(runs: list[dict], key: str) -> float:
    """Get median value for a metric across runs."""
    values = [run[key] for run in runs]
    return statistics.median(values)


def format_delta(
    muxy_val: float, starlette_val: float, *, lower_is_better: bool = False
) -> str:
    """Format delta as percentage with +/- sign."""
    if starlette_val == 0:
        return "N/A"

    if lower_is_better:
        delta = ((muxy_val - starlette_val) / starlette_val) * 100
    else:
        delta = ((muxy_val - starlette_val) / starlette_val) * 100

    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f}%"


def extract_stats(results: dict) -> dict:
    """Extract statistics from results."""
    metadata = results["metadata"]
    muxy_runs = results["results"]["muxy"]
    starlette_runs = results["results"]["starlette"]

    return {
        "metadata": metadata,
        "targets_count": muxy_runs[0]["targets_count"],
        "muxy": {
            "rps": get_median(muxy_runs, "rps"),
            "p50": get_median(muxy_runs, "latency_p50_ms"),
            "p99": get_median(muxy_runs, "latency_p99_ms"),
            "requests": int(get_median(muxy_runs, "requests")),
            "runs": muxy_runs,
            "errors": sum(r["errors"] for r in muxy_runs),
        },
        "starlette": {
            "rps": get_median(starlette_runs, "rps"),
            "p50": get_median(starlette_runs, "latency_p50_ms"),
            "p99": get_median(starlette_runs, "latency_p99_ms"),
            "requests": int(get_median(starlette_runs, "requests")),
            "runs": starlette_runs,
            "errors": sum(r["errors"] for r in starlette_runs),
        },
    }


def print_terminal(stats: dict) -> None:
    """Print formatted comparison summary to terminal."""
    metadata = stats["metadata"]
    muxy = stats["muxy"]
    starlette = stats["starlette"]
    system = metadata["system"]

    print()
    print("=" * 60)
    print("  muxy vs starlette benchmark results")
    print("=" * 60)
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

    print("-" * 60)
    print(f"  {'Metric':<17} {'muxy':>12} {'starlette':>12} {'delta':>12}")
    print("-" * 60)

    rps_delta = format_delta(muxy["rps"], starlette["rps"])
    print(
        f"  {'Requests/sec':<17} {muxy['rps']:>12,.0f} {starlette['rps']:>12,.0f} {rps_delta:>12}"
    )

    p50_delta = format_delta(muxy["p50"], starlette["p50"], lower_is_better=True)
    print(
        f"  {'Latency p50 (ms)':<17} {muxy['p50']:>12,.2f} {starlette['p50']:>12,.2f} {p50_delta:>12}"
    )

    p99_delta = format_delta(muxy["p99"], starlette["p99"], lower_is_better=True)
    print(
        f"  {'Latency p99 (ms)':<17} {muxy['p99']:>12,.2f} {starlette['p99']:>12,.2f} {p99_delta:>12}"
    )

    print(
        f"  {'Total requests':<17} {muxy['requests']:>12,} {starlette['requests']:>12,}"
    )

    print("-" * 60)

    print()
    print("  Individual runs (rps):")
    print(f"    muxy:      {', '.join(f'{r["rps"]:,.0f}' for r in muxy['runs'])}")
    print(f"    starlette: {', '.join(f'{r["rps"]:,.0f}' for r in starlette['runs'])}")

    if muxy["errors"] > 0 or starlette["errors"] > 0:
        print()
        print(f"  Errors: muxy={muxy['errors']}, starlette={starlette['errors']}")

    print()


def format_markdown(stats: dict) -> str:
    """Format results as markdown."""
    metadata = stats["metadata"]
    muxy = stats["muxy"]
    starlette = stats["starlette"]
    system = metadata["system"]

    rps_delta = format_delta(muxy["rps"], starlette["rps"])
    p50_delta = format_delta(muxy["p50"], starlette["p50"], lower_is_better=True)
    p99_delta = format_delta(muxy["p99"], starlette["p99"], lower_is_better=True)

    lines = [
        "## Results",
        "",
        "| Metric | muxy | starlette | delta |",
        "|--------|------|-----------|-------|",
        f"| Requests/sec | {muxy['rps']:,.0f} | {starlette['rps']:,.0f} | {rps_delta} |",
        f"| Latency p50 | {muxy['p50']:,.2f}ms | {starlette['p50']:,.2f}ms | {p50_delta} |",
        f"| Latency p99 | {muxy['p99']:,.2f}ms | {starlette['p99']:,.2f}ms | {p99_delta} |",
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
            f"- muxy: {', '.join(f'{r["rps"]:,.0f}' for r in muxy['runs'])}",
            f"- starlette: {', '.join(f'{r["rps"]:,.0f}' for r in starlette['runs'])}",
            "",
            "</details>",
        ]
    )

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
