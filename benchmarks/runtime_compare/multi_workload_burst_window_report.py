#!/usr/bin/env python3
"""Build before/during/after burst-window reporting for multi-workload runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "multi-workload-burst-window-report-v1"
TELEMETRY_KEYS = [
    "ram_used_mb_avg",
    "ram_used_mb_max",
    "gr3d_freq_pct_avg",
    "gr3d_freq_pct_max",
    "cpu_busy_pct_avg",
    "cpu_busy_pct_max",
    "gpu_temp_c_max",
    "vdd_in_mw_avg",
    "vdd_in_mw_max",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    except Exception as exc:
        return {"command": command, "error": repr(exc)}


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def summarize_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "min": None, "p50": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return ordered[int(rank)]
        return ordered[low] * (high - rank) + ordered[high] * (rank - low)

    return {
        "count": len(values),
        "mean": _round(statistics.fmean(values)),
        "min": _round(min(values)),
        "p50": _round(percentile(0.50)),
        "p95": _round(percentile(0.95)),
        "p99": _round(percentile(0.99)),
        "max": _round(max(values)),
    }


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    operations: dict[str, int] = {}
    for event in events:
        operation = str(event.get("operation", "unknown"))
        operations[operation] = operations.get(operation, 0) + 1
    return {
        "event_count": len(events),
        "success_count": sum(1 for event in events if event.get("ok") is True),
        "error_count": sum(1 for event in events if event.get("ok") is not True),
        "latency_ms": summarize_values([float(event["duration_ms"]) for event in events if event.get("duration_ms") is not None]),
        "operations": dict(sorted(operations.items())),
    }


def events_in_window(events: list[dict[str, Any]], start_s: float, end_s: float) -> list[dict[str, Any]]:
    return [event for event in events if start_s <= float(event.get("started_at_s", -1)) < end_s]


def buckets_overlapping(buckets: list[dict[str, Any]], start_s: float, end_s: float) -> list[dict[str, Any]]:
    return [bucket for bucket in buckets if float(bucket["end_s"]) > start_s and float(bucket["start_s"]) < end_s]


def summarize_telemetry(buckets: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [bucket["telemetry"] for bucket in buckets if bucket.get("telemetry", {}).get("status") == "parsed"]
    if not parsed:
        return {"sample_count": 0, "bucket_count": len(buckets), "status": "no_samples"}
    summary: dict[str, Any] = {"status": "parsed", "bucket_count": len(buckets), "sample_count": sum(int(item.get("sample_count", 0)) for item in parsed)}
    for key in TELEMETRY_KEYS:
        values = [float(item[key]) for item in parsed if item.get(key) is not None]
        if not values:
            summary[key] = None
        elif key.endswith("_max"):
            summary[key] = _round(max(values), 3)
        else:
            summary[key] = _round(statistics.fmean(values), 3)
    return summary


def delta(current: dict[str, Any], baseline: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in keys:
        left = current.get(key)
        right = baseline.get(key)
        output[key] = _round(float(left) - float(right), 4) if left is not None and right is not None else None
    return output


def workload_latency_delta(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for workload, current_summary in current.items():
        base_summary = baseline.get(workload, {})
        current_latency = current_summary.get("latency_ms", {})
        base_latency = base_summary.get("latency_ms", {})
        output[workload] = delta(current_latency, base_latency, ["p50", "p95", "p99", "max"])
    return output


def summarize_window(events_by_workload: dict[str, list[dict[str, Any]]], buckets: list[dict[str, Any]], start_s: float, end_s: float) -> dict[str, Any]:
    window_events = {workload: events_in_window(events, start_s, end_s) for workload, events in events_by_workload.items()}
    return {
        "start_s": _round(start_s),
        "end_s": _round(end_s),
        "duration_s": _round(max(0.0, end_s - start_s)),
        "workloads": {workload: summarize_events(events) for workload, events in sorted(window_events.items())},
        "telemetry": summarize_telemetry(buckets_overlapping(buckets, start_s, end_s)),
    }


def aggregate_phase_windows(windows: list[dict[str, Any]], phase: str, events_by_workload: dict[str, list[dict[str, Any]]], buckets: list[dict[str, Any]]) -> dict[str, Any]:
    ranges = [(float(item[phase]["start_s"]), float(item[phase]["end_s"])) for item in windows]
    event_groups: dict[str, list[dict[str, Any]]] = {workload: [] for workload in events_by_workload}
    for workload, events in events_by_workload.items():
        for event in events:
            start = float(event.get("started_at_s", -1))
            if any(start_s <= start < end_s for start_s, end_s in ranges):
                event_groups[workload].append(event)
    selected_buckets = []
    seen = set()
    for start_s, end_s in ranges:
        for bucket in buckets_overlapping(buckets, start_s, end_s):
            index = bucket["index"]
            if index not in seen:
                selected_buckets.append(bucket)
                seen.add(index)
    return {
        "phase": phase,
        "workloads": {workload: summarize_events(events) for workload, events in sorted(event_groups.items())},
        "telemetry": summarize_telemetry(selected_buckets),
        "window_count": len(ranges),
    }


def build_report(source_path: Path, timeline_path: Path, repo_root: Path, before_sec: float, after_sec: float) -> dict[str, Any]:
    source = read_json(source_path)
    timeline = read_json(timeline_path)
    source_result = source["result"]
    timeline_result = timeline["result"]
    if source_result.get("success") is not True or timeline_result.get("success") is not True:
        raise ValueError("burst-window report requires successful source and timeline artifacts")
    events_by_workload: dict[str, list[dict[str, Any]]] = {}
    for event in source_result["timeline"]:
        events_by_workload.setdefault(str(event.get("workload", "unknown")), []).append(event)
    buckets = timeline_result["buckets"]
    duration_s = float(source_result["scenario"]["duration_s"])
    windows = []
    for burst in timeline_result["whisper_bursts"]:
        burst_start = float(burst["started_at_s"])
        burst_end = float(burst["ended_at_s"])
        before_start = max(0.0, burst_start - before_sec)
        after_end = min(duration_s, burst_end + after_sec)
        item = {
            "burst_index": burst.get("burst_index"),
            "burst_duration_ms": burst.get("duration_ms"),
            "before": summarize_window(events_by_workload, buckets, before_start, burst_start),
            "during": summarize_window(events_by_workload, buckets, burst_start, burst_end),
            "after": summarize_window(events_by_workload, buckets, burst_end, after_end),
        }
        item["deltas"] = {
            "during_minus_before_latency_ms": workload_latency_delta(item["during"]["workloads"], item["before"]["workloads"]),
            "after_minus_before_latency_ms": workload_latency_delta(item["after"]["workloads"], item["before"]["workloads"]),
            "during_minus_before_telemetry": delta(item["during"]["telemetry"], item["before"]["telemetry"], TELEMETRY_KEYS),
            "after_minus_before_telemetry": delta(item["after"]["telemetry"], item["before"]["telemetry"], TELEMETRY_KEYS),
        }
        windows.append(item)

    aggregates = {phase: aggregate_phase_windows(windows, phase, events_by_workload, buckets) for phase in ["before", "during", "after"]}
    aggregate_deltas = {
        "during_minus_before_latency_ms": workload_latency_delta(aggregates["during"]["workloads"], aggregates["before"]["workloads"]),
        "after_minus_before_latency_ms": workload_latency_delta(aggregates["after"]["workloads"], aggregates["before"]["workloads"]),
        "during_minus_before_telemetry": delta(aggregates["during"]["telemetry"], aggregates["before"]["telemetry"], TELEMETRY_KEYS),
        "after_minus_before_telemetry": delta(aggregates["after"]["telemetry"], aggregates["before"]["telemetry"], TELEMETRY_KEYS),
    }
    source_rel = display_path(source_path, repo_root)
    timeline_rel = display_path(timeline_path, repo_root)
    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_json": source_rel,
            "source_sha256": sha256_file(source_path),
            "timeline_json": timeline_rel,
            "timeline_sha256": sha256_file(timeline_path),
            "source_git_commit": source["metadata"].get("git_commit", {}),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "before_window_sec": before_sec,
            "after_window_sec": after_sec,
            "hostname": source["metadata"].get("hostname", ""),
            "power_mode": source["metadata"].get("power_mode", {}),
        },
        "result": {
            "status": "succeeded",
            "success": True,
            "task": "multi_workload_burst_window_report",
            "duration_s": duration_s,
            "burst_count": len(windows),
            "windows": windows,
            "aggregate_by_phase": aggregates,
            "aggregate_deltas": aggregate_deltas,
            "interpretation": {
                "deployment_ready_claim": False,
                "production_stress_test_claim": False,
                "accuracy_claim": False,
                "notes": [
                    "Burst-window reporting compares before/during/after windows around Whisper requests.",
                    "Latency statistics are event-level; telemetry summaries are timeline-bucket-level.",
                    "This is runtime reliability evidence, not a production stress or capacity result.",
                ],
            },
        },
    }


def _fmt(value: Any) -> str:
    return "n/a" if value is None else str(value)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    metadata = report["metadata"]
    result = report["result"]
    aggregate = result["aggregate_by_phase"]
    lines = [
        "# Multi-Workload Burst Window Report",
        "",
        "> Whisper burst 전/중/후 window별 workload latency와 `tegrastats` telemetry 변화를 정리한 보고서입니다.",
        "> 이 보고서는 runtime reliability signal 분석용이며 production stress test나 deployment-ready proof가 아닙니다.",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source JSON | `{metadata['source_json']}` |",
        f"| Timeline JSON | `{metadata['timeline_json']}` |",
        f"| Before window | {metadata['before_window_sec']} s |",
        f"| After window | {metadata['after_window_sec']} s |",
        f"| Burst count | {result['burst_count']} |",
        "",
        "## Aggregate Latency By Phase",
        "",
        "| Phase | Workload | Events | P50 ms | P95 ms | P99 ms | Max ms | Errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for phase in ["before", "during", "after"]:
        for workload, summary in aggregate[phase]["workloads"].items():
            latency = summary["latency_ms"]
            lines.append(f"| {phase} | {workload} | {summary['event_count']} | {_fmt(latency['p50'])} | {_fmt(latency['p95'])} | {_fmt(latency['p99'])} | {_fmt(latency['max'])} | {summary['error_count']} |")
    lines.extend(["", "## Aggregate Telemetry By Phase", "", "| Phase | Samples | GR3D avg % | CPU avg % | RAM avg MB | GPU temp max C | VDD_IN avg mW |", "|---|---:|---:|---:|---:|---:|---:|"])
    for phase in ["before", "during", "after"]:
        telemetry = aggregate[phase]["telemetry"]
        lines.append(f"| {phase} | {telemetry.get('sample_count')} | {_fmt(telemetry.get('gr3d_freq_pct_avg'))} | {_fmt(telemetry.get('cpu_busy_pct_avg'))} | {_fmt(telemetry.get('ram_used_mb_avg'))} | {_fmt(telemetry.get('gpu_temp_c_max'))} | {_fmt(telemetry.get('vdd_in_mw_avg'))} |")
    lines.extend(["", "## Aggregate Deltas", "", "| Delta | Metric | Value |", "|---|---|---:|"])
    for name, values in result["aggregate_deltas"].items():
        if "latency" in name:
            for workload, latency_delta in values.items():
                for metric in ["p50", "p95", "p99", "max"]:
                    lines.append(f"| {name} | {workload}.{metric} | {_fmt(latency_delta.get(metric))} |")
        else:
            for metric, value in values.items():
                lines.append(f"| {name} | {metric} | {_fmt(value)} |")
    lines.extend(["", "## Per-Burst Summary", "", "| Burst | Phase | FastAPI p99 ms | YOLO p99 ms | Whisper max ms | GR3D avg % | CPU avg % |", "|---:|---|---:|---:|---:|---:|---:|"])
    for window in result["windows"]:
        for phase in ["before", "during", "after"]:
            phase_data = window[phase]
            workloads = phase_data["workloads"]
            telemetry = phase_data["telemetry"]
            fastapi_p99 = workloads.get("fastapi_resnet18", {}).get("latency_ms", {}).get("p99")
            yolo_p99 = workloads.get("yolo_detection", {}).get("latency_ms", {}).get("p99")
            whisper_max = workloads.get("fastapi_whisper", {}).get("latency_ms", {}).get("max")
            lines.append(f"| {window['burst_index']} | {phase} | {_fmt(fastapi_p99)} | {_fmt(yolo_p99)} | {_fmt(whisper_max)} | {_fmt(telemetry.get('gr3d_freq_pct_avg'))} | {_fmt(telemetry.get('cpu_busy_pct_avg'))} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- Latency windows are event-level summaries around Whisper bursts.",
        "- Telemetry windows are compact timeline-bucket summaries, not raw sensor replay.",
        "- Treat spikes and deltas as runtime reliability signals, not deployment capacity proof.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export before/during/after burst-window latency and telemetry report.")
    parser.add_argument("--multi-workload", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--before-sec", type=float, default=60.0)
    parser.add_argument("--after-sec", type=float, default=60.0)
    args = parser.parse_args()
    if args.before_sec <= 0 or args.after_sec <= 0:
        raise SystemExit("--before-sec and --after-sec must be positive")
    payload = build_report(args.multi_workload, args.timeline, Path.cwd(), args.before_sec, args.after_sec)
    write_json(args.output, payload)
    print(args.output)
    if args.report is not None:
        write_markdown(payload, args.report)
        print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
