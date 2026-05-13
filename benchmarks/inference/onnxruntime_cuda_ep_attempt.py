#!/usr/bin/env python3
"""Record an isolated ONNX Runtime Execution Provider activation attempt.

The goal is to capture whether a requested Execution Provider can be activated for the
existing ResNet18 ONNX artifact without mutating the current Python environment.
Unavailable and failed states are valid evidence outcomes.
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


SENSITIVE_REPLACEMENTS = (
    ("/home/risenano01", "[home]"),
    ("risenano01", "jetson-user"),
    ("nano01", "jetson-host"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sanitize_text(value: str) -> str:
    sanitized = value
    for needle, replacement in SENSITIVE_REPLACEMENTS:
        sanitized = sanitized.replace(needle, replacement)
    return sanitized


def run_command(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": sanitize_text(completed.stdout.strip()),
            "stderr": sanitize_text(completed.stderr.strip()),
        }
    except Exception as exc:
        return {"command": command, "error": sanitize_text(repr(exc))}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tensorrt_model_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = payload["result"]
        model = result.get("model", {})
        artifacts = result.get("artifacts", {})
        return {
            "architecture": model.get("architecture", "resnet18"),
            "weights": model.get("weights", "random_seeded_weights_no_pretrained_accuracy_claim"),
            "seed": model.get("seed", 42),
            "state_dict_sha256": model.get("state_dict_sha256", ""),
            "onnx_sha256_from_tensorrt": artifacts.get("onnx_sha256", ""),
        }
    except Exception:
        return {}


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


def provider_display_name(provider: str) -> str:
    return {
        "CUDAExecutionProvider": "CUDA",
        "TensorrtExecutionProvider": "TensorRT",
        "CPUExecutionProvider": "CPU",
    }.get(provider, provider.replace("ExecutionProvider", ""))


def provider_schema_version(provider: str) -> str:
    return {
        "CUDAExecutionProvider": "onnxruntime-cuda-ep-attempt-v1",
        "TensorrtExecutionProvider": "onnxruntime-tensorrt-ep-attempt-v1",
        "CPUExecutionProvider": "onnxruntime-cpu-ep-attempt-v1",
    }.get(provider, "onnxruntime-ep-attempt-v1")


def provider_task(provider: str) -> str:
    return {
        "CUDAExecutionProvider": "onnxruntime_cuda_execution_provider_activation_attempt",
        "TensorrtExecutionProvider": "onnxruntime_tensorrt_execution_provider_activation_attempt",
        "CPUExecutionProvider": "onnxruntime_cpu_execution_provider_activation_attempt",
    }.get(provider, "onnxruntime_execution_provider_activation_attempt")


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    attempt = result["activation_attempt"]
    provider = attempt["requested_provider"]
    provider_name = provider_display_name(provider)
    latency = result.get("latency", {})
    latency_mean = latency.get("mean_ms", "not measured")
    latency_p95 = latency.get("p95_ms", "not measured")
    return "\n".join([
        f"# ONNX Runtime {provider_name} EP Activation Attempt", "",
        f"> 격리 원칙을 유지하면서 ONNX Runtime {provider} 활성화 가능 여부를 기록한 evidence입니다.",
        "> 성공, 실패, unavailable 상태를 모두 정상적인 실험 결과로 남깁니다.", "",
        "## Run Information", "", "| Field | Value |", "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['conda_env']}` |",
        f"| Python | `{meta['python_executable']}` / {meta['python_version']} |",
        f"| ONNX Runtime | {meta['onnxruntime']['version']} |",
        f"| PyTorch | {meta['pytorch'].get('version', 'unavailable')} |",
        f"| Torch CUDA available | {meta['pytorch'].get('cuda_available', False)} |",
        f"| Available ORT providers | `{meta['onnxruntime']['available_providers']}` |",
        f"| Result JSON | `{meta['result_json']}` |", "",
        "## Isolation Policy", "", "| Field | Value |", "|---|---|",
        f"| Existing env modified | {meta['isolation']['existing_env_modified']} |",
        f"| Install command executed by this runner | {meta['isolation']['install_command_executed']} |",
        f"| Intended install target | `{meta['isolation']['intended_install_target']}` |",
        f"| Preload strategy | `{meta['isolation']['preload_strategy']}` |", "",
        "## Activation Result", "", "| Field | Value |", "|---|---|",
        f"| Requested provider | `{attempt['requested_provider']}` |",
        f"| Requested provider available | {attempt['requested_available']} |",
        f"| Activation status | `{attempt['status']}` |",
        f"| Session providers | `{attempt.get('session_providers', [])}` |",
        f"| Failure reason | `{attempt.get('failure_reason', '')}` |",
        f"| Mean ms | {latency_mean} |",
        f"| P95 ms | {latency_p95} |", "",
        "## Interpretation", "",
        "- This script does not install packages or modify the current environment.",
        f"- If {provider} is unavailable, the next step is an isolated conda/venv or Docker install attempt rather than changing `yolo_env` in place.",
        f"- If activation succeeds, the measured latency can become the ONNX Runtime {provider_name} candidate for the runtime comparison matrix.",
        "- This evidence remains runtime/provider validation, not deployment readiness or accuracy evidence.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Record ONNX Runtime CUDA EP activation evidence.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--onnx", type=Path, default=Path("models/resnet18_random_seed42_opset17.onnx"))
    parser.add_argument("--tensorrt-json", type=Path, default=Path("results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json"))
    parser.add_argument("--provider", default="CUDAExecutionProvider")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch_info: dict[str, Any] = {"available": False}
    try:
        import torch

        torch_info = {
            "available": True,
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        }
    except Exception as exc:
        torch_info = {"available": False, "error": sanitize_text(repr(exc))}

    import onnxruntime as ort

    available_providers = ort.get_available_providers()
    requested_available = args.provider in available_providers
    activation_attempt: dict[str, Any] = {
        "requested_provider": args.provider,
        "requested_available": requested_available,
        "status": "unavailable",
        "session_providers": [],
        "failure_reason": "",
    }
    latency: dict[str, Any] = {"samples_ms": [], "count": 0}
    output_summary: dict[str, Any] = {}

    if requested_available:
        try:
            rng = np.random.default_rng(args.seed)
            input_shape = [args.batch_size, 3, args.height, args.width]
            inputs = rng.random(input_shape, dtype=np.float32)
            session = ort.InferenceSession(str(args.onnx), providers=[args.provider, "CPUExecutionProvider"])
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name

            def work() -> np.ndarray:
                return session.run([output_name], {input_name: inputs})[0]

            latency, output = timed_repeats(work, args.repeat, args.warmup)
            top_indices = np.argsort(output[0])[-5:][::-1].tolist()
            output_summary = {"top_indices": top_indices, "top_values": [round(float(output[0][index]), 6) for index in top_indices]}
            activation_attempt.update({"status": "succeeded", "session_providers": session.get_providers(), "input_name": input_name, "output_name": output_name})
        except Exception as exc:
            activation_attempt.update({"status": "failed", "failure_reason": sanitize_text(repr(exc))})
    else:
        activation_attempt["failure_reason"] = f"{args.provider} is not in available_providers"

    model_meta = load_tensorrt_model_meta(args.tensorrt_json)
    onnx_sha = sha256_file(args.onnx)
    try:
        result_rel = str(args.output.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        result_rel = str(args.output)

    payload = {
        "metadata": {
            "schema_version": provider_schema_version(args.provider),
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": "python3 (yolo_env)" if os.environ.get("CONDA_DEFAULT_ENV") == "yolo_env" else Path(sys.executable).name,
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "cuda_toolkit": run_command(["nvcc", "--version"]),
            "pytorch": torch_info,
            "onnxruntime": {"version": ort.__version__, "available_providers": available_providers},
            "isolation": {
                "existing_env_modified": False,
                "install_command_executed": False,
                "intended_install_target": "separate conda/venv or Docker image",
                "preload_strategy": "import torch before onnxruntime",
            },
            "result_json": result_rel,
        },
        "result": {
            "task": provider_task(args.provider),
            "framework": "onnxruntime",
            "backend": args.provider,
            "precision": "fp32",
            "model": {
                "architecture": model_meta.get("architecture", "resnet18"),
                "weights": model_meta.get("weights", "random_seeded_weights_no_pretrained_accuracy_claim"),
                "state_dict_sha256": model_meta.get("state_dict_sha256", ""),
                "onnx_path": str(args.onnx),
                "onnx_sha256": onnx_sha,
                "onnx_sha256_matches_tensorrt_source": bool(model_meta.get("onnx_sha256_from_tensorrt")) and model_meta.get("onnx_sha256_from_tensorrt") == onnx_sha,
            },
            "input": {"source": "synthetic_random_numpy_array", "shape": [args.batch_size, 3, args.height, args.width], "dtype": "float32", "seed": args.seed},
            "runtime": {"warmup": args.warmup, "repeat": args.repeat, "timing": "wall_clock_session_run_if_provider_activates"},
            "activation_attempt": activation_attempt,
            "latency": latency,
            "output_summary": output_summary,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(build_report(payload), encoding="utf-8")
    print(args.output)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
