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
    yolo_smoke = repo / "results" / "inference" / "yolo_yolov8n_detection_20260516_010734.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_yolo"
        report = Path(tmp) / "yolo_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_yolo_detection_inferedge.py"),
                "--yolo-smoke",
                str(yolo_smoke),
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
    assert result["runtime_role"] == "object-detection-result"
    assert result["engine_backend"] == "ultralytics"
    assert result["model_name"] == "yolov8n.pt"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["object_detection_ready"] is True
    assert result["extra"]["accuracy_claim"] is False
    assert result["extra"]["deployment_ready_claim"] is False
    assert result["extra"]["external_camera_dependency"] is False
    assert result["comparison"]["verdict"] == "object_detection_smoke_not_accuracy_benchmark"
    assert result["object_detection"]["detection_count"] == 6
    assert result["object_detection"]["class_counts"]["bus"] == 1
    assert result["object_detection"]["input_path"] == "[site-packages]/ultralytics/assets/bus.jpg"
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "ultralytics"
    assert metadata["source_model"]["sha256"] == result["object_detection"]["model_sha256"]
    assert "repo_commit" not in metadata["export"]
    assert "repo_status" not in metadata["export"]
    assert metadata["export"]["source_smoke_commit"] == read_json(yolo_smoke)["metadata"]["git_commit"]
    assert metadata["export"]["export_workspace_commit"]["stdout"]
    assert metadata["export"]["artifact_commit_note"]
    assert "YOLO Detection InferEdge Export Report" in markdown

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        failed_smoke = tmp_path / "yolo_failed.json"
        failed_payload = read_json(yolo_smoke)
        failed_payload["result"]["success"] = False
        failed_payload["result"]["status"] = "dependency_missing"
        failed_smoke.write_text(json.dumps(failed_payload), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_yolo_detection_inferedge.py"),
                "--yolo-smoke",
                str(failed_smoke),
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
