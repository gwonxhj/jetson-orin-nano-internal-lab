#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    env_python = Path.home() / "miniconda3" / "envs" / "ort_cuda_env" / "bin" / "python"
    python = str(env_python) if env_python.exists() else sys.executable
    if not env_python.exists():
        probe = subprocess.run([python, "-c", "import onnxruntime as ort; print(ort.get_available_providers())"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
        if "TensorrtExecutionProvider" not in probe.stdout:
            print("skip: TensorrtExecutionProvider unavailable")
            return 0
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "ort_trt_cache.json"
        report = Path(tmp) / "ort_trt_cache.md"
        cache_dir = Path(tmp) / "cache"
        env = os.environ.copy()
        env.pop("CONDA_DEFAULT_ENV", None)
        subprocess.run([
            python,
            str(repo / "benchmarks" / "inference" / "onnxruntime_tensorrt_cache_bench.py"),
            "--output",
            str(output),
            "--report",
            str(report),
            "--onnx",
            "models/resnet18_random_seed42_opset17.onnx",
            "--cache-dir",
            str(cache_dir),
            "--warmup",
            "0",
            "--repeat",
            "1",
            "--clear-cache",
        ], cwd=repo, env=env, check=True)
        payload = json.loads(output.read_text(encoding="utf-8"))
        markdown = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "onnxruntime-tensorrt-cache-bench-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    result = payload["result"]
    assert result["backend"] == "TensorrtExecutionProvider"
    assert result["provider_options"]["trt_engine_cache_enable"] is True
    assert result["provider_options"]["trt_engine_cache_prefix"] == "resnet18_fp32"
    assert result["phases"]["cold_build"]["session_create_ms"] >= 0
    assert result["phases"]["warm_cache"]["session_create_ms"] >= 0
    assert result["model"]["onnx_sha256_matches_tensorrt_source"] is True
    assert "ONNX Runtime TensorRT EP Engine Cache Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
