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
        signal = tmp_path / "signal.json"
        report = tmp_path / "signal.md"
        subprocess.run([sys.executable, str(repo / "benchmarks" / "runtime_compare" / "multi_workload_timeline_export.py"), "--multi-workload", str(source), "--output", str(timeline), "--bucket-sec", "5"], cwd=repo, check=True)
        subprocess.run([sys.executable, str(repo / "benchmarks" / "runtime_compare" / "multi_workload_burst_window_report.py"), "--multi-workload", str(source), "--timeline", str(timeline), "--output", str(burst), "--before-sec", "5", "--after-sec", "5"], cwd=repo, check=True)
        subprocess.run([sys.executable, str(repo / "benchmarks" / "runtime_compare" / "multi_workload_degradation_signal.py"), "--multi-workload", str(source), "--timeline", str(timeline), "--burst-windows", str(burst), "--output", str(signal), "--report", str(report)], cwd=repo, check=True)
        payload = json.loads(signal.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "multi-workload-degradation-signal-v1"
    result = payload["result"]
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["task"] == "multi_workload_bounded_degradation_signal"
    assert result["interpretation"]["deployment_ready_claim"] is False
    assert result["interpretation"]["production_stress_test_claim"] is False
    assert result["interpretation"]["capacity_plan_claim"] is False
    assert "fastapi_resnet18" in result["event_summary"]
    assert "during_minus_before_telemetry" in result["signals"]
    assert "Multi-Workload Degradation Signal Report" in markdown
    assert "production stress test" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
