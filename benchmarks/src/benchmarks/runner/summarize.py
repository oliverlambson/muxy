"""Summarize benchmark results and print comparison table."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def load_results(path: str) -> dict:
    """Load benchmark results from JSON file."""
    with open(path) as f:
        return json.load(f)


def get_median(runs: list[dict], key: str) -> float:
    """Get median value for a metric across runs."""
    values = [run[key] for run in runs]
    return statistics.median(values)


def format_number(n: float, decimals: int = 2) -> str:
    """Format number with comma separators."""
    if decimals == 0:
        return f"{int(n):,}"
    return f"{n:,.{decimals}f}"


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
        "targets_count": muxy_runs[0].get("targets_count", "?"),
        "muxy": {
            "rps": get_median(muxy_runs, "rps"),
            "p50": get_median(muxy_runs, "latency_p50_ms"),
            "p99": get_median(muxy_runs, "latency_p99_ms"),
            "requests": int(get_median(muxy_runs, "requests")),
            "runs": muxy_runs,
            "errors": sum(r.get("errors", 0) for r in muxy_runs),
        },
        "starlette": {
            "rps": get_median(starlette_runs, "rps"),
            "p50": get_median(starlette_runs, "latency_p50_ms"),
            "p99": get_median(starlette_runs, "latency_p99_ms"),
            "requests": int(get_median(starlette_runs, "requests")),
            "runs": starlette_runs,
            "errors": sum(r.get("errors", 0) for r in starlette_runs),
        },
    }


def print_terminal(stats: dict) -> None:
    """Print formatted comparison summary to terminal."""
    metadata = stats["metadata"]
    muxy = stats["muxy"]
    starlette = stats["starlette"]
    system = metadata.get("system", {})

    print()
    print("=" * 60)
    print("  muxy vs starlette benchmark results")
    print("=" * 60)
    print()
    timestamp = metadata.get("timestamp", "")
    if timestamp:
        date_part = timestamp.split("T")[0] if "T" in timestamp else timestamp
        print(f"  Date:   {date_part}")
    if system:
        print(f"  Device: {system.get('device', 'Unknown')}")
        print(f"  CPU:    {system.get('cpu', 'Unknown')}")
        print(
            f"          {system.get('cores', '?')} cores, {system.get('memory_gb', '?')}GB RAM"
        )
    print()
    print(f"  Routes exercised: {stats['targets_count']}")
    print(f"  Duration: {metadata['duration_sec']}s x {metadata['runs']} runs")
    print(f"  Connections: {metadata['connections']}, Threads: {metadata['threads']}")
    print()

    print("-" * 60)
    print(f"  {'Metric':<20} {'muxy':>12} {'starlette':>12} {'delta':>12}")
    print("-" * 60)

    rps_delta = format_delta(muxy["rps"], starlette["rps"])
    print(
        f"  {'Requests/sec':<20} {format_number(muxy['rps'], 0):>12} {format_number(starlette['rps'], 0):>12} {rps_delta:>12}"
    )

    p50_delta = format_delta(muxy["p50"], starlette["p50"], lower_is_better=True)
    print(
        f"  {'Latency p50 (ms)':<20} {format_number(muxy['p50']):>12} {format_number(starlette['p50']):>12} {p50_delta:>12}"
    )

    p99_delta = format_delta(muxy["p99"], starlette["p99"], lower_is_better=True)
    print(
        f"  {'Latency p99 (ms)':<20} {format_number(muxy['p99']):>12} {format_number(starlette['p99']):>12} {p99_delta:>12}"
    )

    print(
        f"  {'Total requests':<20} {format_number(muxy['requests'], 0):>12} {format_number(starlette['requests'], 0):>12}"
    )

    print("-" * 60)

    print()
    print("  Individual runs (rps):")
    print(
        f"    muxy:      {', '.join(format_number(r['rps'], 0) for r in muxy['runs'])}"
    )
    print(
        f"    starlette: {', '.join(format_number(r['rps'], 0) for r in starlette['runs'])}"
    )

    if muxy["errors"] > 0 or starlette["errors"] > 0:
        print()
        print(f"  Errors: muxy={muxy['errors']}, starlette={starlette['errors']}")

    print()


def format_markdown(stats: dict) -> str:
    """Format results as markdown."""
    metadata = stats["metadata"]
    muxy = stats["muxy"]
    starlette = stats["starlette"]
    system = metadata.get("system", {})

    rps_delta = format_delta(muxy["rps"], starlette["rps"])
    p50_delta = format_delta(muxy["p50"], starlette["p50"], lower_is_better=True)
    p99_delta = format_delta(muxy["p99"], starlette["p99"], lower_is_better=True)

    lines = [
        "## Results",
        "",
        "| Metric | muxy | starlette | delta |",
        "|--------|------|-----------|-------|",
        f"| Requests/sec | {format_number(muxy['rps'], 0)} | {format_number(starlette['rps'], 0)} | {rps_delta} |",
        f"| Latency p50 | {format_number(muxy['p50'])}ms | {format_number(starlette['p50'])}ms | {p50_delta} |",
        f"| Latency p99 | {format_number(muxy['p99'])}ms | {format_number(starlette['p99'])}ms | {p99_delta} |",
        "",
        "<details>",
        "<summary>Benchmark details</summary>",
        "",
    ]

    # Add run date
    timestamp = metadata.get("timestamp", "")
    if timestamp:
        # Parse ISO format and display nicely
        date_part = timestamp.split("T")[0] if "T" in timestamp else timestamp
        lines.extend([f"**Date**: {date_part}", ""])

    # Add system info if available
    if system:
        device = system.get("device", "Unknown")
        cpu = system.get("cpu", "Unknown")
        cores = system.get("cores", "?")
        memory = system.get("memory_gb", "?")
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
            f"- muxy: {', '.join(format_number(r['rps'], 0) for r in muxy['runs'])}",
            f"- starlette: {', '.join(format_number(r['rps'], 0) for r in starlette['runs'])}",
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

    results_path = sys.argv[1]
    markdown_mode = "--markdown" in sys.argv

    if not Path(results_path).exists():
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
