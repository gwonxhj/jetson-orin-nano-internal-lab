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
        output = tmp_path / "llm_candidates.json"
        report = tmp_path / "llm_candidates.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "inference" / "llm_env_candidate_probe.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--target-env",
                "llm_env_test",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "llm-env-candidate-probe-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["metadata"]["environment"]["target_env"] == "llm_env_test"
    assert payload["result"]["task"] == "llm_isolated_env_candidate_probe"
    assert payload["result"]["existing_env_modified"] is False
    assert payload["result"]["install_command_executed"] is False
    assert payload["result"]["download_command_executed"] is False
    assert payload["result"]["candidate_count"] >= 2
    assert "LLM Env Candidate Probe" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
