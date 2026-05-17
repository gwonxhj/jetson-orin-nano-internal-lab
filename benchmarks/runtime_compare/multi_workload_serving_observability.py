#!/usr/bin/env python3
"""Extract queue/serving observability from multi-workload evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "multi-workload-serving-observability-v1"


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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _path_count(metrics: dict[str, Any], path: str, field: str) -> int:
    return _int(metrics.get("requests", {}).get("by_path", {}).get(path, {}).get(field, 0))


def build_observability(source_path: Path, repo_root: Path) -> dict[str, Any]:
    source = read_json(source_path)
    result = source["result"]
    if result.get("success") is not True:
        raise ValueError("serving observability export requires a successful multi-workload source artifact")

    serving = result.get("serving_observability", {})
    client = serving.get("client_backlog_proxy", {})
    server_after = serving.get("server_metrics_after", {})
    metrics_after = result.get("metrics", {}).get("after", {})
    summary = result.get("summary_by_workload", {})
    resnet_endpoint = result.get("workloads", {}).get("fastapi_resnet18", {}).get("endpoint", "/v1/infer/resnet18/synthetic")
    whisper_endpoint = result.get("workloads", {}).get("fastapi_whisper", {}).get("endpoint", "/v1/infer/whisper/speech")

    client_workloads = client.get("workloads", {})
    max_client_outstanding = max((_int(item.get("max_outstanding")) for item in client_workloads.values()), default=0)
    client_failed = _int(client.get("totals", {}).get("failed_count"))
    server_failed = _int(server_after.get("failed_requests"))
    dropped_proxy = _int(serving.get("dropped_request_count_proxy"), client_failed + server_failed)

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_json": display_path(source_path, repo_root),
            "source_sha256": sha256_file(source_path),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "source_git_commit": source["metadata"].get("git_commit", {}),
            "hostname": source["metadata"].get("hostname", ""),
            "power_mode": source["metadata"].get("power_mode", {}),
        },
        "result": {
            "status": "succeeded",
            "success": True,
            "task": "multi_workload_queue_serving_observability",
            "duration_s": result["scenario"]["duration_s"],
            "target_duration_s": result["scenario"]["target_duration_s"],
            "workload_mix": result["scenario"]["workload_mix"],
            "client_backlog_proxy": client,
            "server_inprocess_counters": server_after,
            "request_counts": {
                "client_completed_count": _int(client.get("totals", {}).get("completed_count")),
                "client_failed_count": client_failed,
                "server_total_requests": _int(metrics_after.get("requests", {}).get("total")),
                "server_failed_requests": server_failed,
                "resnet_endpoint_count": _path_count(metrics_after, resnet_endpoint, "count"),
                "resnet_endpoint_failed_count": _path_count(metrics_after, resnet_endpoint, "failed_count"),
                "whisper_endpoint_count": _path_count(metrics_after, whisper_endpoint, "count"),
                "whisper_endpoint_failed_count": _path_count(metrics_after, whisper_endpoint, "failed_count"),
            },
            "signals": {
                "max_client_outstanding": max_client_outstanding,
                "max_server_inflight_requests": _int(server_after.get("max_inflight_requests")),
                "client_failed_requests": client_failed,
                "server_failed_requests": server_failed,
                "dropped_request_count_proxy": dropped_proxy,
                "backlog_proxy_observed": max_client_outstanding > 1 or _int(server_after.get("max_inflight_requests")) > 1,
                "failed_or_dropped_observed": (client_failed + server_failed + dropped_proxy) > 0,
            },
            "workload_error_summary": {
                workload: {"events": item.get("event_count"), "success": item.get("success_count"), "errors": item.get("error_count")}
                for workload, item in summary.items()
            },
            "interpretation": {
                "runtime_reliability_signal": True,
                "deployment_ready_claim": False,
                "production_queue_depth_claim": False,
                "production_stress_test_claim": False,
                "notes": [
                    "Server-side counters are in-process FastAPI metrics exposed by /metrics.",
                    "Client-side outstanding counts are a bounded backlog proxy for this localhost evidence run.",
                    "Dropped request count is represented as failed-request proxy unless a production queue exposes explicit drops.",
                ],
            },
        },
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    metadata = payload["metadata"]
    result = payload["result"]
    counts = result["request_counts"]
    signals = result["signals"]
    lines = [
        "# Multi-Workload Serving Observability Report",
        "",
        "> FastAPI server/client queue, backlog, failed-request proxy를 multi-workload runtime evidence에서 분리한 보고서입니다.",
        "> 이 보고서는 localhost serving reliability evidence이며 production queue-depth telemetry나 deployment-ready proof가 아닙니다.",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source JSON | `{metadata['source_json']}` |",
        f"| Duration | {result['duration_s']} s |",
        f"| Target duration | {result['target_duration_s']} s |",
        "",
        "## Request Counts",
        "",
        "| Signal | Value |",
        "|---|---:|",
    ]
    for key, value in counts.items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## Queue / Backlog Proxy Signals",
        "",
        "| Signal | Value |",
        "|---|---:|",
    ])
    for key, value in signals.items():
        lines.append(f"| {key} | {value} |")
    lines.extend([
        "",
        "## Workload Error Summary",
        "",
        "| Workload | Events | Success | Errors |",
        "|---|---:|---:|---:|",
    ])
    for workload, item in result["workload_error_summary"].items():
        lines.append(f"| {workload} | {item['events']} | {item['success']} | {item['errors']} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- In-process `max_inflight_requests` and client worker outstanding counts are backlog proxies.",
        "- Failed requests are preserved as dropped-request proxy evidence when explicit queue drops are not available.",
        "- This report supports runtime reliability interpretation, not production capacity planning.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export multi-workload serving observability evidence.")
    parser.add_argument("--multi-workload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    payload = build_observability(args.multi_workload, repo_root)
    write_json(args.output, payload)
    if args.report:
        write_markdown(payload, args.report)
    print(args.output)
    if args.report:
        print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
