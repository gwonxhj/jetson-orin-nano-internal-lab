#!/usr/bin/env python3
"""System smoke benchmarks for Jetson Orin Nano Day 1 baseline.

The goal is not to prove deployment readiness. This script captures small,
repeatable CPU, NumPy, PyTorch, CUDA, and disk smoke measurements together
with enough metadata to interpret the numbers later.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"command": command, "error": repr(exc)}


def summarize(samples_ms: list[float]) -> dict[str, Any]:
    ordered = sorted(samples_ms)
    if not ordered:
        return {"samples_ms": [], "count": 0}

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return ordered[int(rank)]
        return ordered[low] * (high - rank) + ordered[high] * (rank - low)

    return {
        "samples_ms": [round(v, 4) for v in samples_ms],
        "count": len(samples_ms),
        "mean_ms": round(statistics.fmean(samples_ms), 4),
        "min_ms": round(min(samples_ms), 4),
        "p50_ms": round(percentile(0.50), 4),
        "p95_ms": round(percentile(0.95), 4),
        "max_ms": round(max(samples_ms), 4),
    }


def timed_repeats(fn: Callable[[], Any], repeat: int, warmup: int) -> tuple[dict[str, Any], Any]:
    last_value: Any = None
    for _ in range(warmup):
        last_value = fn()

    samples: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        last_value = fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return summarize(samples), last_value


def cpu_python_bench(repeat: int, warmup: int, iterations: int) -> dict[str, Any]:
    def work() -> int:
        total = 0
        for i in range(iterations):
            total += (i * i) % 97
        return total

    stats, checksum = timed_repeats(work, repeat, warmup)
    return {
        "name": "cpu_python_loop",
        "status": "ok",
        "unit": "milliseconds",
        "iterations": iterations,
        "checksum": checksum,
        **stats,
    }


def numpy_matmul_bench(repeat: int, warmup: int, size: int) -> dict[str, Any]:
    try:
        import numpy as np
    except Exception as exc:
        return {"name": "numpy_matmul", "status": "skipped", "reason": repr(exc)}

    rng = np.random.default_rng(42)
    a = rng.random((size, size), dtype=np.float32)
    b = rng.random((size, size), dtype=np.float32)

    def work() -> float:
        c = a @ b
        return float(c[0, 0])

    stats, checksum = timed_repeats(work, repeat, warmup)
    return {
        "name": "numpy_matmul",
        "status": "ok",
        "unit": "milliseconds",
        "shape": [size, size],
        "dtype": "float32",
        "checksum": round(float(checksum), 6),
        **stats,
    }


def torch_matmul_bench(repeat: int, warmup: int, size: int, device: str) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"name": f"torch_{device}_matmul", "status": "skipped", "reason": repr(exc)}

    if device == "cuda" and not torch.cuda.is_available():
        return {"name": "torch_cuda_matmul", "status": "skipped", "reason": "torch.cuda.is_available() is False"}

    torch.manual_seed(42)
    target = torch.device(device)
    a = torch.rand((size, size), dtype=torch.float32, device=target)
    b = torch.rand((size, size), dtype=torch.float32, device=target)

    def work() -> float:
        c = a @ b
        if target.type == "cuda":
            torch.cuda.synchronize()
        return float(c[0, 0].detach().cpu())

    stats, checksum = timed_repeats(work, repeat, warmup)
    return {
        "name": f"torch_{device}_matmul",
        "status": "ok",
        "unit": "milliseconds",
        "shape": [size, size],
        "dtype": "float32",
        "device": device,
        "torch_version": torch.__version__,
        "checksum": round(float(checksum), 6),
        **stats,
    }


def disk_io_bench(repeat: int, warmup: int, mib: int) -> dict[str, Any]:
    payload_size = mib * 1024 * 1024
    payload = os.urandom(payload_size)
    temp_dir = Path(tempfile.gettempdir())
    path = temp_dir / f"jetson_disk_smoke_{os.getpid()}.bin"

    def work() -> int:
        path.write_bytes(payload)
        data = path.read_bytes()
        path.unlink(missing_ok=True)
        return len(data)

    try:
        stats, bytes_read = timed_repeats(work, repeat, warmup)
    finally:
        path.unlink(missing_ok=True)

    mean_ms = stats.get("mean_ms")
    throughput = None
    if isinstance(mean_ms, (int, float)) and mean_ms > 0:
        throughput = round((mib * 2) / (mean_ms / 1000.0), 4)

    return {
        "name": "disk_write_read_smoke",
        "status": "ok",
        "unit": "milliseconds",
        "path": str(temp_dir),
        "mib_written_and_read_per_repeat": mib,
        "bytes_read": bytes_read,
        "approx_total_mib_per_second": throughput,
        **stats,
    }


def build_metadata(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": "system-baseline-v1",
        "generated_at": now_iso(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
        "git_status": run_command(["git", "status", "--short", "--branch"]),
        "power_mode": run_command(["nvpmodel", "-q"]),
        "tegrastats_note": args.tegrastats_log or "not captured by this script",
        "parameters": {
            "repeat": args.repeat,
            "warmup": args.warmup,
            "matmul_size": args.matmul_size,
            "cpu_iterations": args.cpu_iterations,
            "disk_mib": args.disk_mib,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Jetson system smoke benchmarks.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--matmul-size", type=int, default=512)
    parser.add_argument("--cpu-iterations", type=int, default=2_000_000)
    parser.add_argument("--disk-mib", type=int, default=64)
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = [
        cpu_python_bench(args.repeat, args.warmup, args.cpu_iterations),
        numpy_matmul_bench(args.repeat, args.warmup, args.matmul_size),
        torch_matmul_bench(args.repeat, args.warmup, args.matmul_size, "cpu"),
        torch_matmul_bench(args.repeat, args.warmup, args.matmul_size, "cuda"),
        disk_io_bench(args.repeat, args.warmup, args.disk_mib),
    ]

    payload = {
        "metadata": build_metadata(args),
        "result": {
            "summary": "Jetson Orin Nano Day 1 system smoke baseline",
            "benchmarks": results,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
