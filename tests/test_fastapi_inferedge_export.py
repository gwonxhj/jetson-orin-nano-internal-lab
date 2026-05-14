#!/usr/bin/env python3
from __future__ import annotations

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
    fastapi_smoke = repo / "results" / "inference" / "fastapi_resnet18_server_20260514_142053.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_serving"
        report = Path(tmp) / "fastapi_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_fastapi_serving_inferedge.py"),
                "--fastapi-smoke",
                str(fastapi_smoke),
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
    assert result["runtime_role"] == "serving-result"
    assert result["engine_backend"] == "fastapi+pytorch"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["serving_ready"] is True
    assert result["comparison"]["verdict"] == "serving_layer_evidence_not_direct_regression"
    assert result["serving"]["endpoint"] == "/v1/infer/resnet18/synthetic"
    assert result["serving"]["latency_layers"]["client_roundtrip_ms"]["mean_ms"] >= result["serving"]["latency_layers"]["server_inference_ms"]["mean_ms"]
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "fastapi+pytorch"
    assert "FastAPI InferEdge Serving Export Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
