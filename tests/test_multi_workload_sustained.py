#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "multi_workload.json"
        report = Path(tmp) / "multi_workload.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_sustained.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--duration-sec",
                "0.35",
                "--fastapi-concurrency",
                "2",
                "--fastapi-interval-sec",
                "0.01",
                "--whisper-start-sec",
                "0.08",
                "--whisper-repeat",
                "2",
                "--whisper-interval-sec",
                "0.02",
                "--yolo-interval-sec",
                "0.02",
                "--mock-workloads",
                "--mock-yolo-ms",
                "3",
                "--mock-fastapi-ms",
                "2",
                "--mock-whisper-ms",
                "8",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "multi-workload-sustained-v1"
    result = payload["result"]
    assert result["task"] == "multi_workload_sustained_runtime_interaction"
    assert result["success"] is True
    assert result["scenario"]["mock_workloads"] is True
    assert result["scenario"]["external_sensor_dependency"] is False
    assert result["workloads"]["fastapi_resnet18"]["concurrency"] == 2
    assert result["workloads"]["fastapi_whisper"]["repeat"] == 2
    assert result["summary_by_workload"]["yolo_detection"]["success_count"] >= 1
    assert result["summary_by_workload"]["fastapi_resnet18"]["success_count"] >= 1
    assert result["summary_by_workload"]["fastapi_whisper"]["success_count"] == 2
    assert result["interaction"]["whisper_window_present"] is True
    serving = result["serving_observability"]
    assert serving["client_backlog_proxy"]["workloads"]["fastapi_resnet18"]["max_outstanding"] >= 1
    assert serving["client_backlog_proxy"]["workloads"]["fastapi_whisper"]["completed_count"] == 2
    assert serving["failed_request_count"] == 0
    assert serving["dropped_request_count_proxy"] == 0
    assert result["timeline"][0]["details"].get("client_backlog_proxy_kind") in {None, "thread_inflight_request_count"}
    assert result["interpretation"]["deployment_ready_claim"] is False
    assert result["interpretation"]["production_stress_test_claim"] is False
    assert "Multi-Workload Sustained Runtime Report" in markdown
    assert "production stress test" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
