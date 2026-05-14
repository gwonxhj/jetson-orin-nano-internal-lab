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
    whisper_smoke = repo / "results" / "inference" / "whisper_tiny_speech_transcription_20260514_182822.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge_whisper"
        report = Path(tmp) / "whisper_inferedge_export.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "export_whisper_inferedge.py"),
                "--whisper-smoke",
                str(whisper_smoke),
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
    assert result["runtime_role"] == "audio-transcription-result"
    assert result["engine_backend"] == "openai-whisper"
    assert result["extra"]["compare_ready"] is True
    assert result["extra"]["transcription_ready"] is True
    assert result["extra"]["expected_text_matched"] is True
    assert result["comparison"]["verdict"] == "audio_transcription_smoke_not_accuracy_benchmark"
    assert result["audio"]["path"] == "examples/audio/license_clear_whisper_smoke.wav"
    assert result["transcription"]["expected_text"] == "hello world"
    assert result["transcription"]["normalized_contains_expected"] is True
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "openai-whisper"
    assert "Whisper InferEdge Export Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
