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
    fastapi_whisper_smoke = repo / "results" / "inference" / "fastapi_whisper_speech_server_20260514_202459.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_fastapi_whisper"
        report = Path(tmp) / "fastapi_whisper_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_fastapi_whisper_serving_inferedge.py"),
                "--fastapi-whisper-smoke",
                str(fastapi_whisper_smoke),
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
    assert result["engine_backend"] == "fastapi+openai-whisper"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["serving_ready"] is True
    assert result["extra"]["transcription_ready"] is True
    assert result["extra"]["expected_text_matched"] is True
    assert result["comparison"]["verdict"] == "serving_layer_evidence_not_direct_regression"
    assert result["serving"]["endpoint"] == "/v1/infer/whisper/speech"
    assert result["serving"]["request"]["audio_path"] == "examples/audio/license_clear_whisper_smoke.wav"
    assert result["audio"]["path"] == "examples/audio/license_clear_whisper_smoke.wav"
    assert result["transcription"]["expected_text"] == "hello world"
    assert result["transcription"]["normalized_contains_expected"] is True
    assert result["serving"]["latency_layers"]["client_roundtrip_ms"]["mean_ms"] >= result["serving"]["latency_layers"]["server_transcription_ms"]["mean_ms"]
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "fastapi+openai-whisper"
    assert "repo_commit" not in metadata["export"]
    assert "repo_status" not in metadata["export"]
    assert metadata["export"]["source_smoke_commit"] == read_json(fastapi_whisper_smoke)["metadata"]["git_commit"]
    assert metadata["export"]["export_workspace_commit"]["stdout"]
    assert metadata["export"]["artifact_commit_note"]
    assert "FastAPI Whisper InferEdge Serving Export Report" in markdown

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        failed_smoke = tmp_path / "fastapi_whisper_failed.json"
        failed_payload = read_json(fastapi_whisper_smoke)
        failed_payload["result"]["success"] = False
        failed_payload["result"]["status"] = "dependency_missing"
        failed_smoke.write_text(json.dumps(failed_payload), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_fastapi_whisper_serving_inferedge.py"),
                "--fastapi-whisper-smoke",
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
