#!/usr/bin/env python3
"""PyTorch image model inference smoke benchmark.

This is a runtime smoke benchmark for Jetson evidence. It uses a deterministic
synthetic image tensor and random model weights by default, so the output is not
an accuracy claim. The goal is to prove that the PyTorch CUDA inference path can
run and to preserve enough execution context for later TensorRT comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
        "p99_ms": round(percentile(0.99), 4),
        "max_ms": round(max(samples_ms), 4),
    }


def build_model(model_name: str):
    from torchvision.models import mobilenet_v2, resnet18

    if model_name == "resnet18":
        return resnet18(weights=None)
    if model_name == "mobilenet_v2":
        return mobilenet_v2(weights=None)
    raise ValueError(f"unsupported model: {model_name}")


def state_dict_sha256(model: Any) -> str:
    import torch

    canonical = {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
    buffer = io.BytesIO()
    torch.save(canonical, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def parameter_count(model: Any) -> int:
    return sum(param.numel() for param in model.parameters())


def cuda_metadata(torch: Any) -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"available": False}
    device_index = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device_index)
    return {
        "available": True,
        "device_index": device_index,
        "device_name": torch.cuda.get_device_name(device_index),
        "capability": list(torch.cuda.get_device_capability(device_index)),
        "total_memory_bytes": props.total_memory,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a PyTorch image inference smoke benchmark.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=["resnet18", "mobilenet_v2"], default="resnet18")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    import torch
    import torchvision

    if args.device == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device_name = args.device
    if device_name == "cuda" and not torch.cuda.is_available():
        raise SystemExit("requested CUDA but torch.cuda.is_available() is False")

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = torch.device(device_name)
    model = build_model(args.model).eval().to(device)
    model_hash = state_dict_sha256(model)
    input_shape = [args.batch_size, 3, args.height, args.width]
    inputs = torch.rand(input_shape, dtype=torch.float32, device=device)

    with torch.inference_mode():
        for _ in range(args.warmup):
            _ = model(inputs)
            if device.type == "cuda":
                torch.cuda.synchronize()

        samples_ms: list[float] = []
        last_output = None
        for _ in range(args.repeat):
            start = time.perf_counter()
            last_output = model(inputs)
            if device.type == "cuda":
                torch.cuda.synchronize()
            samples_ms.append((time.perf_counter() - start) * 1000.0)

    assert last_output is not None
    output_cpu = last_output.detach().cpu()
    top_values, top_indices = torch.topk(output_cpu[0], k=min(5, output_cpu.shape[-1]))

    payload = {
        "metadata": {
            "schema_version": "inference-smoke-v1",
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
        },
        "result": {
            "task": "image_classification_smoke",
            "framework": "pytorch",
            "backend": device.type,
            "precision": "fp32",
            "model": {
                "architecture": args.model,
                "weights": "random_seeded_weights_no_pretrained_accuracy_claim",
                "parameter_count": parameter_count(model),
                "state_dict_sha256": model_hash,
            },
            "input": {
                "source": "synthetic_random_tensor",
                "shape": input_shape,
                "dtype": "float32",
                "seed": args.seed,
                "preprocessing_included": False,
                "postprocessing_included": False,
            },
            "runtime": {
                "torch_version": torch.__version__,
                "torchvision_version": torchvision.__version__,
                "cuda": cuda_metadata(torch),
                "warmup": args.warmup,
                "repeat": args.repeat,
            },
            "latency": summarize(samples_ms),
            "output": {
                "shape": list(output_cpu.shape),
                "top5_indices": [int(v) for v in top_indices.tolist()],
                "top5_values": [round(float(v), 6) for v in top_values.tolist()],
            },
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
