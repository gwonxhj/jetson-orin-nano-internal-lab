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
        output = Path(tmp) / "ort_cuda_candidates.json"
        report = Path(tmp) / "ort_cuda_candidates.md"
        subprocess.run([
            sys.executable,
            str(repo / "benchmarks" / "inference" / "ort_cuda_wheel_candidate_probe.py"),
            "--output",
            str(output),
            "--report",
            str(report),
            "--skip-network",
        ], cwd=repo, check=True)
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "ort-cuda-wheel-candidate-probe-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["result"]["existing_env_modified"] is False
    assert payload["result"]["install_command_executed"] is False
    assert payload["result"]["candidate_count"] >= 2
    names = {item["name"] for item in payload["result"]["candidates"]}
    assert "jetson_ai_lab_index_jp6_cu126" in names
    assert "jetson_ai_lab_direct_wheel_1_20_2" in names
    assert "ONNX Runtime CUDA Env Candidate Probe" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
