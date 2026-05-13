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
        output = Path(tmp) / "system_baseline_test.json"
        subprocess.run(
            [
                sys.executable,
                str(repo / "benchmarks/system/system_smoke_bench.py"),
                "--output",
                str(output),
                "--repeat",
                "1",
                "--warmup",
                "0",
                "--matmul-size",
                "16",
                "--cpu-iterations",
                "1000",
                "--disk-mib",
                "1",
            ],
            check=True,
            cwd=repo,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["metadata"]["schema_version"] == "system-baseline-v1"
    assert "generated_at" in payload["metadata"]
    assert "parameters" in payload["metadata"]
    assert payload["result"]["summary"]
    benches = payload["result"]["benchmarks"]
    assert len(benches) == 5
    assert {bench["name"] for bench in benches} >= {
        "cpu_python_loop",
        "numpy_matmul",
        "torch_cpu_matmul",
        "torch_cuda_matmul",
        "disk_write_read_smoke",
    }
    for bench in benches:
        assert bench["status"] in {"ok", "skipped"}
        if bench["status"] == "ok":
            assert bench["count"] == 1
            assert isinstance(bench["mean_ms"], (int, float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
