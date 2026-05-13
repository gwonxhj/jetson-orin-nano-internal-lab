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
        out = Path(tmp) / "compare.json"
        md = Path(tmp) / "compare.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks" / "runtime_compare" / "build_runtime_comparison.py"),
                "--output",
                str(out),
                "--markdown",
                str(md),
            ],
            cwd=repo,
            check=True,
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        markdown = md.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "runtime-compare-v1"
    result = payload["result"]
    assert result["comparison_name"] == "resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_tensorrt_fp16"
    assert [runtime["name"] for runtime in result["runtimes"]] == ["pytorch_cuda", "onnxruntime_cpu", "tensorrt_trtexec"]
    assert result["comparability"]["same_model_hash"] is True
    assert result["comparability"]["same_input_shape"] is True
    assert result["comparability"]["same_precision"] is False
    assert result["comparability"]["verdict"] == "runtime_comparison_not_direct_regression"
    assert result["ratios"]["mean_latency_pytorch_over_tensorrt"] > 1.0
    assert result["ratios"]["mean_latency_onnxruntime_over_tensorrt"] > 1.0
    assert "ONNX Runtime CPU" in markdown
    assert "Runtime Comparison Report" in markdown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
