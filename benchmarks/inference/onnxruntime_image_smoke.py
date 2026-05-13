#!/usr/bin/env python3
"""ONNX Runtime image model inference smoke benchmark.

This uses the existing ResNet18 ONNX artifact and records ONNX Runtime provider
availability separately from the measured provider. It is runtime evidence, not
an accuracy claim.
"""

from __future__ import annotations

import argparse
import hashlib
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

import numpy as np


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
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


def provider_status(ort: Any, requested_provider: str) -> dict[str, Any]:
    available = ort.get_available_providers()
    return {
        "available_providers": available,
        "requested_provider": requested_provider,
        "requested_available": requested_provider in available,
        "cpu_available": "CPUExecutionProvider" in available,
        "cuda_available": "CUDAExecutionProvider" in available,
        "cuda_note": "CUDAExecutionProvider unavailable in this yolo_env ONNX Runtime build" if "CUDAExecutionProvider" not in available else "CUDAExecutionProvider available",
    }


def load_tensorrt_model_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        model = payload["result"].get("model", {})
        artifacts = payload["result"].get("artifacts", {})
        return {
            "architecture": model.get("architecture", "resnet18"),
            "weights": model.get("weights", "random_seeded_weights_no_pretrained_accuracy_claim"),
            "seed": model.get("seed", 42),
            "state_dict_sha256": model.get("state_dict_sha256", ""),
            "onnx_sha256_from_tensorrt": artifacts.get("onnx_sha256", ""),
        }
    except Exception:
        return {}


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    latency = result["latency"]
    providers = meta["onnxruntime"]["provider_status"]
    return "\n".join([
        "# ONNX Runtime Inference Smoke Report", "",
        "> ResNet18 ONNX artifact를 ONNX Runtime으로 실행한 smoke evidence입니다.",
        "> Provider availability를 별도로 기록하며, 이 결과는 runtime path evidence이지 accuracy evidence가 아닙니다.", "",
        "## Run Information", "", "| Field | Value |", "|---|---|",
        f"| Date | {meta['generated_at']} |", f"| Hostname | `{meta['hostname']}` |", f"| Conda env | `{meta['conda_env']}` |",
        f"| ONNX Runtime | {meta['onnxruntime']['version']} |", f"| Requested provider | `{providers['requested_provider']}` |",
        f"| Available providers | `{providers['available_providers']}` |", f"| CUDA provider available | {providers['cuda_available']} |",
        f"| Power mode | {meta['power_mode'].get('stdout', '').replace(chr(10), '; ')} |", f"| Result JSON | `{meta['result_json']}` |", f"| Tegrastats log | `{meta['tegrastats_note']}` |", "",
        "## Parameters", "", "| Field | Value |", "|---|---:|", f"| input shape | {result['input']['shape']} |", f"| precision | {result['precision']} |", f"| warmup | {result['runtime']['warmup']} |", f"| repeat | {result['runtime']['repeat']} |", "",
        "## Results", "", "| Runtime | Provider | Mean ms | P95 ms | P99 ms |", "|---|---|---:|---:|---:|", f"| ONNX Runtime | {result['provider']} | {latency['mean_ms']} | {latency['p95_ms']} | {latency['p99_ms']} |", "",
        "## Interpretation", "",
        "- ONNX Runtime CPUExecutionProvider is runnable in the current Jetson Python environment.",
        "- CUDAExecutionProvider is not available in this ONNX Runtime build, so ORT CUDA is recorded as unavailable rather than inferred from PyTorch CUDA availability.",
        "- This smoke uses synthetic input and random seeded model weights; it is not an accuracy claim.",
        "- PyTorch CUDA, ONNX Runtime CPU, and TensorRT FP16 differ in backend/provider/precision, so the comparison should remain runtime comparison evidence, not direct regression evidence.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ONNX Runtime ResNet18 inference smoke.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--onnx", type=Path, default=Path("models/resnet18_random_seed42_opset17.onnx"))
    parser.add_argument("--tensorrt-json", type=Path, default=Path("results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json"))
    parser.add_argument("--provider", default="CPUExecutionProvider")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    import onnxruntime as ort

    providers = provider_status(ort, args.provider)
    if not providers["requested_available"]:
        raise SystemExit(f"requested ONNX Runtime provider is unavailable: {args.provider}; available={providers['available_providers']}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    input_shape = [args.batch_size, 3, args.height, args.width]
    rng = np.random.default_rng(args.seed)
    inputs = rng.random(input_shape, dtype=np.float32)
    session = ort.InferenceSession(str(args.onnx), providers=[args.provider])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    def work() -> np.ndarray:
        return session.run([output_name], {input_name: inputs})[0]

    latency, output = timed_repeats(work, args.repeat, args.warmup)
    top_indices = np.argsort(output[0])[-5:][::-1].tolist()
    top_values = [float(output[0][index]) for index in top_indices]
    model_meta = load_tensorrt_model_meta(args.tensorrt_json)
    model_hash = model_meta.get("state_dict_sha256", "")
    onnx_sha = sha256_file(args.onnx)

    payload = {
        "metadata": {
            "schema_version": "onnxruntime-smoke-v1", "generated_at": now_iso(), "hostname": "jetson-orin-nano", "platform": platform.platform(),
            "python_executable": "python3 (yolo_env)" if os.environ.get("CONDA_DEFAULT_ENV") == "yolo_env" else Path(sys.executable).name,
            "python_version": platform.python_version(), "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]), "git_status": safe_git_status(), "power_mode": run_command(["nvpmodel", "-q"]),
            "onnxruntime": {"version": ort.__version__, "provider_status": providers}, "tegrastats_note": args.tegrastats_log or "not captured by this script", "result_json": str(args.output),
        },
        "result": {
            "task": "image_classification_smoke", "framework": "onnxruntime", "backend": args.provider, "provider": args.provider, "precision": "fp32",
            "model": {"architecture": model_meta.get("architecture", "resnet18"), "weights": model_meta.get("weights", "random_seeded_weights_no_pretrained_accuracy_claim"), "state_dict_sha256": model_hash, "onnx_path": str(args.onnx), "onnx_sha256": onnx_sha, "onnx_sha256_matches_tensorrt_source": bool(model_meta.get("onnx_sha256_from_tensorrt")) and model_meta.get("onnx_sha256_from_tensorrt") == onnx_sha},
            "input": {"source": "synthetic_random_numpy_array", "shape": input_shape, "dtype": "float32", "seed": args.seed, "preprocessing_included": False, "postprocessing_included": "top5_only_after_timing", "input_name": input_name, "output_name": output_name},
            "runtime": {"warmup": args.warmup, "repeat": args.repeat, "timing": "wall_clock_session_run"}, "latency": latency,
            "output_summary": {"top_indices": top_indices, "top_values": [round(v, 6) for v in top_values]},
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
