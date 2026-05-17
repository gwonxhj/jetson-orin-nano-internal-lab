#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    source = repo / "results" / "runtime_compare" / "multi_workload_sustained_20260517_213947.json"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        timeline = tmp_path / "timeline.json"
        burst = tmp_path / "burst.json"
        report = tmp_path / "burst.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_timeline_export.py"),
                "--multi-workload",
                str(source),
                "--output",
                str(timeline),
                "--bucket-sec",
                "5",
            ],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_burst_window_report.py"),
                "--multi-workload",
                str(source),
                "--timeline",
                str(timeline),
                "--output",
                str(burst),
                "--report",
                str(report),
                "--before-sec",
                "5",
                "--after-sec",
                "5",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(burst.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "multi-workload-burst-window-report-v1"
    result = payload["result"]
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["task"] == "multi_workload_burst_window_report"
    assert result["burst_count"] == 1
    assert len(result["windows"]) == 1
    assert result["windows"][0]["during"]["workloads"]["fastapi_whisper"]["success_count"] == 1
    assert result["aggregate_by_phase"]["during"]["workloads"]["fastapi_whisper"]["success_count"] == 1
    assert result["aggregate_by_phase"]["before"]["workloads"]["fastapi_resnet18"]["event_count"] >= 1
    assert result["aggregate_by_phase"]["during"]["telemetry"]["status"] == "parsed"
    assert result["interpretation"]["deployment_ready_claim"] is False
    assert result["interpretation"]["production_stress_test_claim"] is False
    assert "Multi-Workload Burst Window Report" in markdown
    assert "deployment-ready proof" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
