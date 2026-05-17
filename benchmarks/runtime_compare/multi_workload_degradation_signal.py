#!/usr/bin/env python3
"""Summarize bounded multi-workload degradation signals."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "multi-workload-degradation-signal-v1"


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


def get_nested(payload: dict[str, Any], path: list[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_signal(source_path: Path, timeline_path: Path, burst_path: Path, repo_root: Path) -> dict[str, Any]:
    source = read_json(source_path)
    timeline = read_json(timeline_path)
    burst = read_json(burst_path)
    result = source["result"]
    burst_result = burst["result"]
    if result.get("success") is not True or timeline["result"].get("success") is not True or burst_result.get("success") is not True:
        raise ValueError("degradation signal requires successful source, timeline, and burst-window artifacts")

    summary = result["summary_by_workload"]
    aggregate_deltas = burst_result["aggregate_deltas"]
    fastapi_p99_delta = get_nested(aggregate_deltas, ["during_minus_before_latency_ms", "fastapi_resnet18", "p99"])
    fastapi_max_delta = get_nested(aggregate_deltas, ["during_minus_before_latency_ms", "fastapi_resnet18", "max"])
    telemetry_delta = aggregate_deltas.get("during_minus_before_telemetry", {})
    error_count = int(result.get("error_count", 0))
    fastapi_p99_spike = fastapi_p99_delta is not None and float(fastapi_p99_delta) >= 100.0
    fastapi_max_spike = fastapi_max_delta is not None and float(fastapi_max_delta) >= 250.0
    resource_pressure = any(
        telemetry_delta.get(key) is not None and float(telemetry_delta[key]) > threshold
        for key, threshold in {
            "cpu_busy_pct_avg": 2.0,
            "ram_used_mb_avg": 64.0,
            "vdd_in_mw_avg": 100.0,
        }.items()
    )
    error_signal = error_count > 0
    observed = fastapi_p99_spike or fastapi_max_spike or resource_pressure or error_signal
    scenario = result["scenario"]
    workloads = result["workloads"]

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_json": display_path(source_path, repo_root),
            "source_sha256": sha256_file(source_path),
            "timeline_json": display_path(timeline_path, repo_root),
            "timeline_sha256": sha256_file(timeline_path),
            "burst_windows_json": display_path(burst_path, repo_root),
            "burst_windows_sha256": sha256_file(burst_path),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "source_git_commit": source["metadata"].get("git_commit", {}),
            "hostname": source["metadata"].get("hostname", ""),
            "power_mode": source["metadata"].get("power_mode", {}),
        },
        "result": {
            "status": "succeeded",
            "success": True,
            "task": "multi_workload_bounded_degradation_signal",
            "degradation_signal_observed": observed,
            "signal_kind": "bounded_opt_in_runtime_degradation",
            "duration_s": scenario["duration_s"],
            "target_duration_s": scenario["target_duration_s"],
            "workload_mix": scenario["workload_mix"],
            "overload_config": {
                "fastapi_concurrency": workloads["fastapi_resnet18"]["concurrency"],
                "fastapi_interval_s": workloads["fastapi_resnet18"]["interval_s"],
                "whisper_repeat": workloads["fastapi_whisper"]["repeat"],
                "whisper_interval_s": workloads["fastapi_whisper"]["interval_s"],
                "yolo_interval_s": workloads["yolo_detection"]["interval_s"],
            },
            "event_summary": {
                workload: {
                    "events": item["event_count"],
                    "success": item["success_count"],
                    "errors": item["error_count"],
                    "p95_ms": item["latency_ms"].get("p95_ms"),
                    "p99_ms": item["latency_ms"].get("p99_ms"),
                    "max_ms": item["latency_ms"].get("max_ms"),
                }
                for workload, item in summary.items()
            },
            "signals": {
                "fastapi_resnet18_p99_spike": fastapi_p99_spike,
                "fastapi_resnet18_max_spike": fastapi_max_spike,
                "resource_pressure_delta": resource_pressure,
                "runtime_errors_observed": error_signal,
                "during_minus_before_fastapi_p99_ms": _round(fastapi_p99_delta),
                "during_minus_before_fastapi_max_ms": _round(fastapi_max_delta),
                "during_minus_before_telemetry": telemetry_delta,
            },
            "source_reports": {
                "timeline_bucket_count": timeline["result"].get("bucket_count"),
                "burst_count": burst_result.get("burst_count"),
                "burst_window_report": display_path(burst_path, repo_root),
            },
            "interpretation": {
                "runtime_reliability_signal": True,
                "deployment_ready_claim": False,
                "production_stress_test_claim": False,
                "capacity_plan_claim": False,
                "accuracy_claim": False,
                "notes": [
                    "This scenario intentionally raises local concurrency and shorter request intervals to preserve bounded contention evidence.",
                    "A degradation signal can be latency spike, resource pressure, request error, backlog proxy, or fallback behavior.",
                    "This artifact records a reliability signal for analysis, not production readiness or capacity planning.",
                ],
            },
        },
    }


def _fmt(value: Any) -> str:
    return "n/a" if value is None else str(value)


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    metadata = payload["metadata"]
    result = payload["result"]
    signals = result["signals"]
    lines = [
        "# Multi-Workload Degradation Signal Report",
        "",
        "> Opt-in overload/concurrency scenario에서 관찰된 bounded runtime degradation signal을 정리한 보고서입니다.",
        "> 이 보고서는 reliability signal evidence이며 production stress test, capacity plan, deployment-ready proof가 아닙니다.",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source JSON | `{metadata['source_json']}` |",
        f"| Timeline JSON | `{metadata['timeline_json']}` |",
        f"| Burst-window JSON | `{metadata['burst_windows_json']}` |",
        f"| Duration | {result['duration_s']} s |",
        f"| Degradation signal observed | {result['degradation_signal_observed']} |",
        "",
        "## Opt-In Overload Config",
        "",
        "| Field | Value |",
        "|---|---:|",
    ]
    for key, value in result["overload_config"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Event Summary", "", "| Workload | Events | Success | Errors | P95 ms | P99 ms | Max ms |", "|---|---:|---:|---:|---:|---:|---:|"])
    for workload, item in result["event_summary"].items():
        lines.append(f"| {workload} | {item['events']} | {item['success']} | {item['errors']} | {_fmt(item['p95_ms'])} | {_fmt(item['p99_ms'])} | {_fmt(item['max_ms'])} |")
    lines.extend([
        "",
        "## Signals",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| FastAPI p99 spike | {signals['fastapi_resnet18_p99_spike']} |",
        f"| FastAPI max spike | {signals['fastapi_resnet18_max_spike']} |",
        f"| Resource pressure delta | {signals['resource_pressure_delta']} |",
        f"| Runtime errors observed | {signals['runtime_errors_observed']} |",
        f"| During-before FastAPI p99 delta ms | {_fmt(signals['during_minus_before_fastapi_p99_ms'])} |",
        f"| During-before FastAPI max delta ms | {_fmt(signals['during_minus_before_fastapi_max_ms'])} |",
        "",
        "## Telemetry Delta During Minus Before",
        "",
        "| Metric | Delta |",
        "|---|---:|",
    ])
    for key, value in signals["during_minus_before_telemetry"].items():
        lines.append(f"| {key} | {_fmt(value)} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- This is an opt-in bounded overload scenario, not the default benchmark path.",
        "- Signals are preserved even when no request errors occur; latency and resource pressure are reliability signals too.",
        "- Do not use this as a production capacity or deployment-ready claim.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export bounded runtime degradation signal from multi-workload artifacts.")
    parser.add_argument("--multi-workload", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--burst-windows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    payload = build_signal(args.multi_workload, args.timeline, args.burst_windows, Path.cwd())
    write_json(args.output, payload)
    print(args.output)
    if args.report is not None:
        write_markdown(payload, args.report)
        print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
