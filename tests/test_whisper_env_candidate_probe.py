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
        output = Path(tmp) / "whisper_env_candidates.json"
        report = Path(tmp) / "whisper_env_candidates.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "inference" / "whisper_env_candidate_probe.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--target-env",
                "whisper_env_test",
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "whisper-env-candidate-probe-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["metadata"]["environment"]["target_env"] == "whisper_env_test"
    assert payload["result"]["existing_env_modified"] is False
    assert payload["result"]["install_command_executed"] is False
    assert payload["result"]["download_command_executed"] is False
    assert payload["result"]["candidate_count"] == 2
    backends = {candidate["backend"] for candidate in payload["result"]["candidates"]}
    assert backends == {"openai-whisper", "faster-whisper"}
    assert "Whisper Env Candidate Probe" in markdown
    assert "Keep `yolo_env` unchanged" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
