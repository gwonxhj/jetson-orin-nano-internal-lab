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
        output = tmp_path / "whisper_smoke.json"
        report = tmp_path / "whisper_smoke.md"
        audio = tmp_path / "whisper_smoke.wav"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "inference" / "whisper_transcription_smoke.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--audio",
                str(audio),
                "--model",
                "tiny",
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

    assert payload["metadata"]["schema_version"] == "whisper-transcription-smoke-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["metadata"]["isolation"]["existing_env_modified"] is False
    assert payload["metadata"]["isolation"]["install_command_executed"] is False
    assert payload["result"]["task"] == "audio_transcription_smoke"
    assert payload["result"]["model"]["name"] == "tiny"
    assert payload["result"]["audio"]["sample_rate_hz"] == 16000
    assert payload["result"]["audio"]["duration_s"] == 1.0
    assert payload["result"]["status"] in {"succeeded", "failed", "dependency_missing", "model_missing"}
    assert payload["result"]["interpretation"]["accuracy_claim"] is False
    assert "Whisper Transcription Smoke Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
