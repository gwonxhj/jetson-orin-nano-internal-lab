#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_inferedge_artifacts import validate_all  # noqa: E402


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    summary = validate_all(repo, strict_files=True)
    assert summary["success"] is True
    assert summary["validated_count"] >= 5
    assert summary["error_count"] == 0
    roles = {entry["runtime_role"] for entry in summary["entries"]}
    assert "runtime-result" in roles
    assert "serving-result" in roles
    assert "audio-transcription-result" in roles
    assert "text-generation-result" in roles

    completed = subprocess.run(
        [sys.executable, str(repo / "scripts" / "validate_inferedge_artifacts.py"), "--root", str(repo), "--json"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    cli_summary = json.loads(completed.stdout)
    assert cli_summary["success"] is True
    assert cli_summary["validated_count"] == summary["validated_count"]

    source_dir = repo / "results" / "inferedge" / "llm_tiny-gpt2_text_generation_20260515_005755"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        target_dir = tmp_root / "results" / "inferedge" / source_dir.name
        target_dir.parent.mkdir(parents=True)
        shutil.copytree(source_dir, target_dir)
        result_path = target_dir / "result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["extra"]["quality_claim"] = True
        result_path.write_text(json.dumps(payload), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable,
                str(repo / "scripts" / "validate_inferedge_artifacts.py"),
                "--root",
                str(tmp_root),
                "--skip-artifact-files",
            ],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        assert failed.returncode != 0
        assert "quality or deployment readiness" in failed.stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
