#!/usr/bin/env python3
"""Export ResNet18 to ONNX and build/run a TensorRT FP16 engine with trtexec."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import shlex
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], timeout: int | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "command_text": shlex.join(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "elapsed_sec": round(time.perf_counter() - start, 4),
    }


def command_metadata(command: list[str]) -> dict[str, Any]:
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


def parse_trtexec_metrics(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    label_map = {
        "GPU Compute Time": "gpu_compute_time_ms",
        "Latency": "latency_ms",
        "Enqueue Time": "enqueue_time_ms",
        "H2D Latency": "h2d_latency_ms",
        "D2H Latency": "d2h_latency_ms",
    }

    for line in text.splitlines():
        stripped = line.strip()
        for label, key in label_map.items():
            marker = f"{label}:"
            has_label = stripped.startswith(marker) or re.search(r"\]\s+\[I\]\s+" + re.escape(marker), line)
            if not has_label:
                continue
            values = {
                name: float(value)
                for name, value in re.findall(r"(min|max|mean|median|percentile\(90%\)|percentile\(95%\)|percentile\(99%\))\s*=\s*([0-9.]+)\s*ms", line)
            }
            if values:
                metrics[key] = {
                    "min": values.get("min"),
                    "max": values.get("max"),
                    "mean": values.get("mean"),
                    "median": values.get("median"),
                    "p90": values.get("percentile(90%)"),
                    "p95": values.get("percentile(95%)"),
                    "p99": values.get("percentile(99%)"),
                }

    throughput = re.search(r"Throughput:\s*([0-9.]+)\s*qps", text)
    if throughput:
        metrics["throughput_qps"] = float(throughput.group(1))

    if "latency_ms" in metrics and metrics["latency_ms"].get("p99") is not None:
        metrics["percentile_99_ms"] = metrics["latency_ms"]["p99"]
    return metrics


def build_model(model_name: str):
    from torchvision.models import resnet18

    if model_name != "resnet18":
        raise ValueError(f"unsupported model: {model_name}")
    return resnet18(weights=None)


def state_dict_sha256(model: Any) -> str:
    import torch

    canonical = {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
    buffer = io.BytesIO()
    torch.save(canonical, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def export_onnx(args: argparse.Namespace, onnx_path: Path) -> dict[str, Any]:
    import torch

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    model = build_model(args.model).eval().cpu()
    model_hash = state_dict_sha256(model)
    sample = torch.rand([args.batch_size, 3, args.height, args.width], dtype=torch.float32)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample,
        onnx_path,
        export_params=True,
        opset_version=args.opset,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
    )
    return {
        "architecture": args.model,
        "weights": "random_seeded_weights_no_pretrained_accuracy_claim",
        "seed": args.seed,
        "state_dict_sha256": model_hash,
        "input_name": "input",
        "output_name": "output",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and run a ResNet18 TensorRT FP16 trtexec smoke.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--onnx", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--build-log", type=Path, required=True)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--model", default="resnet18")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--warmup-ms", type=int, default=500)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--trtexec", default="/usr/src/tensorrt/bin/trtexec")
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    import torch
    import torchvision

    model_meta = export_onnx(args, args.onnx)
    args.engine.parent.mkdir(parents=True, exist_ok=True)
    args.build_log.parent.mkdir(parents=True, exist_ok=True)
    args.run_log.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    build_command = [
        args.trtexec,
        f"--onnx={args.onnx}",
        f"--saveEngine={args.engine}",
        "--fp16",
    ]
    run_command_args = [
        args.trtexec,
        f"--loadEngine={args.engine}",
        f"--warmUp={args.warmup_ms}",
        f"--iterations={args.iterations}",
    ]

    build = run_command(build_command, timeout=600)
    args.build_log.write_text(build["stdout"], encoding="utf-8")
    if build["exit_code"] != 0:
        raise SystemExit(f"trtexec build failed, see {args.build_log}")

    run = run_command(run_command_args, timeout=600)
    args.run_log.write_text(run["stdout"], encoding="utf-8")
    if run["exit_code"] != 0:
        raise SystemExit(f"trtexec run failed, see {args.run_log}")

    payload = {
        "metadata": {
            "schema_version": "tensorrt-smoke-v1",
            "generated_at": now_iso(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": command_metadata(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": command_metadata(["git", "status", "--short", "--branch"]),
            "power_mode": command_metadata(["nvpmodel", "-q"]),
            "trtexec_version": command_metadata([args.trtexec, "--version"]),
            "tegrastats_note": args.tegrastats_log or "not captured by this script",
        },
        "result": {
            "task": "tensorrt_resnet18_fp16_smoke",
            "source_framework": "pytorch",
            "runtime": "tensorrt",
            "precision": "fp16",
            "input_shape": [args.batch_size, 3, args.height, args.width],
            "batch_size": args.batch_size,
            "model": model_meta,
            "artifacts": {
                "onnx_path": str(args.onnx),
                "onnx_sha256": sha256_file(args.onnx),
                "onnx_bytes": args.onnx.stat().st_size,
                "engine_path": str(args.engine),
                "engine_sha256": sha256_file(args.engine),
                "engine_bytes": args.engine.stat().st_size,
                "build_log": str(args.build_log),
                "run_log": str(args.run_log),
            },
            "commands": {
                "build": build["command_text"],
                "run": run["command_text"],
            },
            "protocol": {
                "warmup_ms": args.warmup_ms,
                "iterations": args.iterations,
                "preprocessing_included": False,
                "postprocessing_included": False,
            },
            "metrics": parse_trtexec_metrics(run["stdout"]),
            "build_elapsed_sec": build["elapsed_sec"],
            "run_elapsed_sec": run["elapsed_sec"],
            "torch_version": torch.__version__,
            "torchvision_version": torchvision.__version__,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
