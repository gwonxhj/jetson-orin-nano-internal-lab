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
        output = Path(tmp) / "cuda_compute_test.json"
        report = Path(tmp) / "cuda_compute_test.md"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks/cuda/cuda_compute_smoke.py"),
                "--output",
                str(output),
                "--report",
                str(report),
                "--repeat",
                "1",
                "--warmup",
                "0",
                "--matmul-size",
                "16",
                "--vector-elements",
                "1024",
                "--transfer-mib",
                "1",
            ],
            check=True,
            cwd=repo,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        report_text = report.read_text(encoding="utf-8")

    assert payload["metadata"]["schema_version"] == "cuda-compute-smoke-v1"
    assert payload["metadata"]["hostname"] == "jetson-orin-nano"
    assert "parameters" in payload["metadata"]
    assert payload["result"]["summary"]
    benches = payload["result"]["benchmarks"]
    assert {bench["name"] for bench in benches} == {
        "torch_cpu_matmul",
        "torch_cuda_matmul",
        "cuda_elementwise_add",
        "cuda_h2d_transfer",
        "cuda_d2h_transfer",
    }
    for bench in benches:
        assert bench["status"] in {"ok", "skipped"}
        if bench["status"] == "ok":
            assert bench["count"] == 1
            assert isinstance(bench["mean_ms"], (int, float))
            assert bench["unit"] == "milliseconds"
    assert "CUDA Compute Smoke Notes" in report_text
    assert "deployment readiness" in report_text
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
