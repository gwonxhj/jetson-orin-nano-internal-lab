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
        output = tmp_path / "llm_smoke.json"
        report = tmp_path / "llm_smoke.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "inference" / "llm_text_generation_smoke.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--model-alias",
                "tiny-gpt2",
                "--model-id",
                "local-test-model-not-present",
                "--prompt",
                "Jetson edge AI",
                "--max-new-tokens",
                "4",
                "--warmup",
                "0",
                "--repeat",
                "1",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "llm-text-generation-smoke-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["metadata"]["isolation"]["existing_env_modified"] is False
    assert payload["metadata"]["isolation"]["install_command_executed"] is False
    assert payload["metadata"]["isolation"]["download_allowed"] is False
    assert payload["metadata"]["isolation"]["offline_only"] is True
    assert payload["result"]["task"] == "llm_text_generation_smoke"
    assert payload["result"]["framework"] == "transformers"
    assert payload["result"]["model"]["id"] == "local-test-model-not-present"
    assert payload["result"]["status"] in {"succeeded", "failed", "dependency_missing", "model_missing"}
    assert payload["result"]["interpretation"]["quality_claim"] is False
    assert payload["result"]["interpretation"]["deployment_ready_claim"] is False
    assert "LLM Text Generation Smoke Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
