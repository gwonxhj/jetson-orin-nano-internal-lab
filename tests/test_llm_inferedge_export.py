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
    llm_smoke = repo / "results" / "llm" / "llm_tiny-gpt2_text_generation_20260515_005755.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_llm"
        report = Path(tmp) / "llm_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_llm_inferedge.py"),
                "--llm-smoke",
                str(llm_smoke),
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
    assert result["runtime_role"] == "text-generation-result"
    assert result["engine_backend"] == "transformers"
    assert result["model_name"] == "sshleifer/tiny-gpt2"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["text_generation_ready"] is True
    assert result["extra"]["quality_claim"] is False
    assert result["extra"]["deployment_ready_claim"] is False
    assert result["comparison"]["verdict"] == "text_generation_smoke_not_quality_benchmark"
    assert result["text_generation"]["prompt"] == "Jetson edge AI"
    assert result["text_generation"]["generated_token_count"] == 16
    assert result["comparison"]["ratios"]["generated_tokens_per_second"] > 0
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "transformers"
    assert "repo_commit" not in metadata["export"]
    assert "repo_status" not in metadata["export"]
    assert metadata["export"]["source_smoke_commit"] == read_json(llm_smoke)["metadata"]["git_commit"]
    assert metadata["export"]["export_workspace_commit"]["stdout"]
    assert metadata["export"]["artifact_commit_note"]
    assert "LLM InferEdge Export Report" in markdown

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        failed_smoke = tmp_path / "llm_failed.json"
        failed_payload = read_json(llm_smoke)
        failed_payload["result"]["success"] = False
        failed_payload["result"]["status"] = "dependency_missing"
        failed_smoke.write_text(json.dumps(failed_payload), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_llm_inferedge.py"),
                "--llm-smoke",
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
