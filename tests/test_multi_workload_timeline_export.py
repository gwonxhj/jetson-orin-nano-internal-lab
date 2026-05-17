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
        output = Path(tmp) / "timeline.json"
        report = Path(tmp) / "timeline.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "multi_workload_timeline_export.py"),
                "--multi-workload",
                str(source),
                "--output",
                str(output),
                "--report",
                str(report),
                "--bucket-sec",
                "5",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "multi-workload-runtime-timeline-v1"
    result = payload["result"]
    assert result["success"] is True
    assert result["status"] == "succeeded"
    assert result["task"] == "multi_workload_runtime_timeline_export"
    assert result["bucket_count"] >= 1
    assert result["source_event_count"] >= 1
    assert result["telemetry_sample_count"] >= 1
    assert result["workload_totals"]["fastapi_resnet18"]["success_count"] >= 1
    assert result["workload_totals"]["fastapi_whisper"]["success_count"] == 1
    assert result["telemetry_summary"]["status"] == "parsed"
    assert result["interpretation"]["deployment_ready_claim"] is False
    assert result["interpretation"]["production_stress_test_claim"] is False
    assert "samples_ms" not in json.dumps(result["buckets"])
    assert "Multi-Workload Runtime Timeline Export" in markdown
    assert "production capacity plan" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
