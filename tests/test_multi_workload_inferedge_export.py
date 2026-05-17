#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import read_json, validate_inferedge_metadata, validate_inferedge_result


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    source = repo / "results" / "runtime_compare" / "multi_workload_sustained_20260517_213947.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_multi_workload"
        report = Path(tmp) / "multi_workload_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_multi_workload_sustained_inferedge.py"),
                "--multi-workload",
                str(source),
                "--output-dir",
                str(out_dir),
                "--report",
                str(report),
            ],
            cwd=repo,
            check=True,
        )
        metadata = read_json(out_dir / "metadata.json")
        result = read_json(out_dir / "result.json")
        markdown = report.read_text(encoding="utf-8")

    validate_inferedge_metadata(metadata)
    validate_inferedge_result(result)
    assert result["schema_version"] == "inferedge-runtime-result-v1"
    assert result["runtime_role"] == "multi-workload-runtime-result"
    assert result["engine_backend"] == "mixed:yolo+fastapi+pytorch+openai-whisper"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["runtime_reliability_ready"] is True
    assert result["extra"]["deployment_ready_claim"] is False
    assert result["extra"]["production_stress_test_claim"] is False
    assert result["extra"]["external_sensor_dependency"] is False
    assert result["comparison"]["verdict"] == "multi_workload_runtime_interaction_evidence_not_production_stress_test"
    assert result["workload_interaction"]["summary_by_workload"]["fastapi_whisper"]["success_count"] == 1
    assert result["workload_interaction"]["interaction"]["whisper_window_present"] is True
    assert result["jetson_evidence"]["tegrastats_summary"]["status"] == "parsed"
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "mixed:yolo+fastapi+pytorch+openai-whisper"
    assert "Multi-Workload InferEdge Export Report" in markdown

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        failed_source = tmp_path / "multi_workload_failed.json"
        failed_payload = read_json(source)
        failed_payload["result"]["success"] = False
        failed_payload["result"]["status"] = "completed_with_runtime_events"
        failed_payload["result"]["error_count"] = 1
        failed_source.write_text(json.dumps(failed_payload), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_multi_workload_sustained_inferedge.py"),
                "--multi-workload",
                str(failed_source),
                "--output-dir",
                str(tmp_path / "failed_export"),
            ],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        assert failed.returncode != 0
        assert "must be successful" in failed.stderr
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
