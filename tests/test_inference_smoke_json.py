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
        output = Path(tmp) / "inference_smoke_test.json"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks/inference/pytorch_image_smoke.py"),
                "--output",
                str(output),
                "--model",
                "resnet18",
                "--device",
                "cpu",
                "--batch-size",
                "1",
                "--height",
                "64",
                "--width",
                "64",
                "--warmup",
                "0",
                "--repeat",
                "1",
            ],
            check=True,
            cwd=repo,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["metadata"]["schema_version"] == "inference-smoke-v1"
    result = payload["result"]
    assert result["task"] == "image_classification_smoke"
    assert result["framework"] == "pytorch"
    assert result["backend"] == "cpu"
    assert result["precision"] == "fp32"
    assert result["model"]["architecture"] == "resnet18"
    assert len(result["model"]["state_dict_sha256"]) == 64
    assert result["input"]["shape"] == [1, 3, 64, 64]
    assert result["latency"]["count"] == 1
    assert result["output"]["shape"] == [1, 1000]
    assert len(result["output"]["top5_indices"]) == 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
