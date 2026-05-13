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
        output = Path(tmp) / "onnxruntime_test.json"
        report = Path(tmp) / "onnxruntime_test.md"
        subprocess.run([
            sys.executable, str(repo / "benchmarks" / "inference" / "onnxruntime_image_smoke.py"), "--output", str(output), "--report", str(report),
            "--onnx", "models/resnet18_random_seed42_opset17.onnx", "--tensorrt-json", "results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json",
            "--provider", "CPUExecutionProvider", "--warmup", "0", "--repeat", "1",
        ], cwd=repo, check=True)
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "onnxruntime-smoke-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    providers = payload["metadata"]["onnxruntime"]["provider_status"]
    assert providers["cpu_available"] is True
    assert payload["result"]["framework"] == "onnxruntime"
    assert payload["result"]["provider"] == "CPUExecutionProvider"
    assert payload["result"]["precision"] == "fp32"
    assert payload["result"]["input"]["shape"] == [1, 3, 224, 224]
    assert payload["result"]["latency"]["count"] == 1
    assert payload["result"]["model"]["onnx_sha256_matches_tensorrt_source"] is True
    assert "ONNX Runtime Inference Smoke Report" in markdown
    assert "CUDAExecutionProvider" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
