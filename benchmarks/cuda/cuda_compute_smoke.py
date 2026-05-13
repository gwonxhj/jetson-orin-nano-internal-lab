#!/usr/bin/env python3
"""CUDA/GPU compute smoke benchmark for Jetson Orin Nano.

This is intentionally separate from model inference benchmarks. It captures
basic CPU/GPU matrix multiplication and host/device transfer costs so later
runtime results can be interpreted with a small compute baseline.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_command(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"command": command, "error": repr(exc)}


def safe_git_status() -> dict[str, Any]:
    status = run_command(["git", "status", "--short", "--branch"])
    if "stdout" in status:
        status["stdout"] = "[captured during evidence generation; see committed git history for final state]"
    return status


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
        "p99_ms": round(percentile(0.99), 4),
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


def torch_info() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"available": False, "error": repr(exc)}

    cuda_available = torch.cuda.is_available()
    info: dict[str, Any] = {
        "available": True,
        "torch_version": torch.__version__,
        "cuda_available": cuda_available,
        "torch_cuda_version": getattr(torch.version, "cuda", None),
        "cudnn_version": torch.backends.cudnn.version() if hasattr(torch.backends, "cudnn") else None,
    }
    if cuda_available:
        info.update(
            {
                "cuda_device_count": torch.cuda.device_count(),
                "cuda_device_name": torch.cuda.get_device_name(0),
                "cuda_capability": list(torch.cuda.get_device_capability(0)),
            }
        )
    return info


def torch_matmul_bench(repeat: int, warmup: int, size: int, device_name: str) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"name": f"torch_{device_name}_matmul", "status": "skipped", "reason": repr(exc)}

    if device_name == "cuda" and not torch.cuda.is_available():
        return {"name": "torch_cuda_matmul", "status": "skipped", "reason": "torch.cuda.is_available() is False"}

    torch.manual_seed(42)
    device = torch.device(device_name)
    a = torch.rand((size, size), dtype=torch.float32, device=device)
    b = torch.rand((size, size), dtype=torch.float32, device=device)

    def work() -> float:
        c = a @ b
        if device.type == "cuda":
            torch.cuda.synchronize()
        return float(c[0, 0].detach().cpu())

    stats, checksum = timed_repeats(work, repeat, warmup)
    return {
        "name": f"torch_{device_name}_matmul",
        "status": "ok",
        "category": "compute",
        "unit": "milliseconds",
        "measurement_method": "wall_clock_with_cuda_synchronize" if device_name == "cuda" else "wall_clock",
        "shape": [size, size],
        "dtype": "float32",
        "device": device_name,
        "checksum": round(float(checksum), 6),
        **stats,
    }


def cuda_elementwise_add_bench(repeat: int, warmup: int, elements: int) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"name": "cuda_elementwise_add", "status": "skipped", "reason": repr(exc)}
    if not torch.cuda.is_available():
        return {"name": "cuda_elementwise_add", "status": "skipped", "reason": "torch.cuda.is_available() is False"}

    torch.manual_seed(42)
    a = torch.rand((elements,), dtype=torch.float32, device="cuda")
    b = torch.rand((elements,), dtype=torch.float32, device="cuda")

    def work() -> float:
        c = a + b
        torch.cuda.synchronize()
        return float(c[0].detach().cpu())

    stats, checksum = timed_repeats(work, repeat, warmup)
    return {
        "name": "cuda_elementwise_add",
        "status": "ok",
        "category": "compute",
        "unit": "milliseconds",
        "measurement_method": "wall_clock_with_cuda_synchronize",
        "elements": elements,
        "approx_input_mib": round((elements * 4 * 2) / (1024 * 1024), 4),
        "dtype": "float32",
        "device": "cuda",
        "checksum": round(float(checksum), 6),
        **stats,
    }


def transfer_bench(repeat: int, warmup: int, transfer_mib: int, direction: str) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"name": f"cuda_{direction}_transfer", "status": "skipped", "reason": repr(exc)}
    if not torch.cuda.is_available():
        return {"name": f"cuda_{direction}_transfer", "status": "skipped", "reason": "torch.cuda.is_available() is False"}

    elements = transfer_mib * 1024 * 1024 // 4
    torch.manual_seed(42)
    cpu_tensor = torch.rand((elements,), dtype=torch.float32, device="cpu")
    cuda_tensor = cpu_tensor.to("cuda")
    torch.cuda.synchronize()

    if direction == "h2d":
        def work() -> float:
            copied = cpu_tensor.to("cuda")
            torch.cuda.synchronize()
            return float(copied[0].detach().cpu())
    elif direction == "d2h":
        def work() -> float:
            copied = cuda_tensor.cpu()
            return float(copied[0])
    else:
        raise ValueError(f"unknown transfer direction: {direction}")

    stats, checksum = timed_repeats(work, repeat, warmup)
    mean_ms = stats.get("mean_ms")
    throughput = None
    if isinstance(mean_ms, (int, float)) and mean_ms > 0:
        throughput = round(transfer_mib / (mean_ms / 1000.0), 4)

    return {
        "name": f"cuda_{direction}_transfer",
        "status": "ok",
        "category": "transfer",
        "unit": "milliseconds",
        "measurement_method": "wall_clock_copy",
        "direction": direction,
        "transfer_mib": transfer_mib,
        "approx_mib_per_second": throughput,
        "dtype": "float32",
        "checksum": round(float(checksum), 6),
        **stats,
    }


def build_metadata(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema_version": "cuda-compute-smoke-v1",
        "generated_at": now_iso(),
        "device": "Jetson Orin Nano",
        "hostname": "jetson-orin-nano",
        "platform": platform.platform(),
        "python_executable": "python3 (yolo_env)" if os.environ.get("CONDA_DEFAULT_ENV") == "yolo_env" else Path(sys.executable).name,
        "python_version": platform.python_version(),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "torch": torch_info(),
        "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
        "git_status": safe_git_status(),
        "power_mode": run_command(["nvpmodel", "-q"]),
        "tegrastats_note": args.tegrastats_log or "not captured by this script",
        "parameters": {
            "repeat": args.repeat,
            "warmup": args.warmup,
            "matmul_size": args.matmul_size,
            "vector_elements": args.vector_elements,
            "transfer_mib": args.transfer_mib,
        },
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    benches = payload["result"]["benchmarks"]
    params = meta["parameters"]

    rows = []
    for bench in benches:
        if bench["status"] == "ok":
            rows.append(
                f"| `{bench['name']}` | {bench.get('category', '')} | {bench.get('device', bench.get('direction', ''))} | "
                f"{bench.get('mean_ms', '')} | {bench.get('p95_ms', '')} | {bench.get('approx_mib_per_second', '')} |"
            )
        else:
            rows.append(f"| `{bench['name']}` | skipped | - | - | - | {bench.get('reason', '')} |")

    return "\n".join(
        [
            "# CUDA Compute Smoke Notes",
            "",
            "> 모델 추론이 아닌 Jetson 내부 GPU compute와 host/device transfer 비용을 분리해서 기록한 smoke evidence입니다.",
            "> 이 결과는 deployment readiness가 아니라 이후 inference/runtime 수치를 해석하기 위한 작은 기준선입니다.",
            "",
            "## Run Information",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Date | {meta['generated_at']} |",
            f"| Device | {meta['device']} |",
            f"| Hostname | `{meta['hostname']}` |",
            f"| Conda env | `{meta['conda_env']}` |",
            f"| Python | {meta['python_version']} |",
            f"| Torch | {meta['torch'].get('torch_version', 'unavailable')} |",
            f"| CUDA available | {meta['torch'].get('cuda_available', False)} |",
            f"| CUDA device | {meta['torch'].get('cuda_device_name', 'unavailable')} |",
            f"| Power mode | {meta['power_mode'].get('stdout', 'unavailable').replace(chr(10), '; ')} |",
            f"| Tegrastats log | `{meta['tegrastats_note']}` |",
            "",
            "## Parameters",
            "",
            "| Field | Value |",
            "|---|---:|",
            f"| repeat | {params['repeat']} |",
            f"| warmup | {params['warmup']} |",
            f"| matmul size | {params['matmul_size']} x {params['matmul_size']} |",
            f"| vector elements | {params['vector_elements']} |",
            f"| transfer size | {params['transfer_mib']} MiB |",
            "",
            "## Results",
            "",
            "| Benchmark | Category | Device / Direction | Mean ms | P95 ms | Transfer MiB/s |",
            "|---|---|---|---:|---:|---:|",
            *rows,
            "",
            "## Interpretation",
            "",
            "- This is a compute/transfer smoke, not a model inference benchmark.",
            "- CPU and GPU numbers should be interpreted with input size and synchronization overhead attached.",
            "- Host/device transfer cost is recorded separately because small workloads can be dominated by movement rather than compute.",
            "- Power mode and tegrastats side log must stay attached before comparing this run with future CUDA or inference runs.",
            "- Short smoke results must not be used as sustained thermal throttling or deployment-readiness evidence.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Jetson CUDA/GPU compute smoke benchmarks.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--matmul-size", type=int, default=1024)
    parser.add_argument("--vector-elements", type=int, default=4_194_304)
    parser.add_argument("--transfer-mib", type=int, default=32)
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = [
        torch_matmul_bench(args.repeat, args.warmup, args.matmul_size, "cpu"),
        torch_matmul_bench(args.repeat, args.warmup, args.matmul_size, "cuda"),
        cuda_elementwise_add_bench(args.repeat, args.warmup, args.vector_elements),
        transfer_bench(args.repeat, args.warmup, args.transfer_mib, "h2d"),
        transfer_bench(args.repeat, args.warmup, args.transfer_mib, "d2h"),
    ]

    payload = {
        "metadata": build_metadata(args),
        "result": {
            "summary": "Jetson Orin Nano CUDA/GPU compute and transfer smoke baseline",
            "benchmarks": results,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(build_report(payload), encoding="utf-8")
        print(args.report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
