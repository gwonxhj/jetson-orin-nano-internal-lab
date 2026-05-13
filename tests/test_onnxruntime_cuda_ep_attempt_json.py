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
        output = Path(tmp) / "onnxruntime_cuda_ep_attempt.json"
        report = Path(tmp) / "onnxruntime_cuda_ep_attempt.md"
        subprocess.run([
            sys.executable,
            str(repo / "benchmarks" / "inference" / "onnxruntime_cuda_ep_attempt.py"),
            "--output",
            str(output),
            "--report",
            str(report),
            "--onnx",
            "models/resnet18_random_seed42_opset17.onnx",
            "--warmup",
            "0",
            "--repeat",
            "1",
        ], cwd=repo, check=True)
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "onnxruntime-cuda-ep-attempt-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert payload["metadata"]["isolation"]["existing_env_modified"] is False
    assert payload["metadata"]["isolation"]["install_command_executed"] is False
    assert payload["result"]["activation_attempt"]["requested_provider"] == "CUDAExecutionProvider"
    assert payload["result"]["activation_attempt"]["status"] in {"succeeded", "failed", "unavailable"}
    assert payload["result"]["input"]["shape"] == [1, 3, 224, 224]
    assert "ONNX Runtime CUDA EP Activation Attempt" in markdown
    assert "Existing env modified | False" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
