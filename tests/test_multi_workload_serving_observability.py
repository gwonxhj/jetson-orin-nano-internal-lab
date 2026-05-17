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
        tmp_path = Path(tmp)
        source = tmp_path / "multi_workload.json"
        source_report = tmp_path / "multi_workload.md"
        output = tmp_path / "serving_observability.json"
        report = tmp_path / "serving_observability.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_sustained.py"),
                "--output",
                str(source),
                "--report",
                str(source_report),
                "--duration-sec",
                "0.35",
                "--fastapi-concurrency",
                "3",
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
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_serving_observability.py"),
                "--multi-workload",
                str(source),
                "--output",
                str(output),
                "--report",
                str(report),
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "multi-workload-serving-observability-v1"
    result = payload["result"]
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["task"] == "multi_workload_queue_serving_observability"
    assert result["request_counts"]["client_failed_count"] == 0
    assert result["signals"]["max_client_outstanding"] >= 1
    assert result["signals"]["client_failed_requests"] == 0
    assert result["signals"]["dropped_request_count_proxy"] == 0
    assert result["interpretation"]["deployment_ready_claim"] is False
    assert result["interpretation"]["production_queue_depth_claim"] is False
    assert "Multi-Workload Serving Observability Report" in markdown
    assert "production queue-depth" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
