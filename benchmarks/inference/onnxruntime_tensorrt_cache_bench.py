#!/usr/bin/env python3
"""Measure ONNX Runtime TensorRT EP engine cache behavior.

This benchmark records provider options, cold session creation, warm cached
session creation, first-run latency, repeated session.run latency, and cache
artifact hashes for the existing ResNet18 ONNX artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np


SENSITIVE_REPLACEMENTS = (
    (str(Path.home()), "[home]"),
    (Path.home().name, "jetson-user"),
    (platform.node().split(".", 1)[0], "jetson-host"),
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
            "command": [sanitize_text(part) for part in command],
            "exit_code": completed.returncode,
            "stdout": sanitize_text(completed.stdout.strip()),
            "stderr": sanitize_text(completed.stderr.strip()),
        }
    except Exception as exc:
        return {"command": [sanitize_text(part) for part in command], "error": sanitize_text(repr(exc))}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return sanitize_text(str(path))


def safe_git_status() -> dict[str, Any]:
    status = run_command(["git", "status", "--short", "--branch"])
    if "stdout" in status:
        status["stdout"] = "[captured during evidence generation; see committed git history for final state]"
    return status


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
            "state_dict_sha256": model.get("state_dict_sha256", ""),
            "onnx_sha256_from_tensorrt": artifacts.get("onnx_sha256", ""),
        }
    except Exception:
        return {}


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


def first_run_ms(fn: Callable[[], Any]) -> tuple[float, Any]:
    start = time.perf_counter()
    output = fn()
    return round((time.perf_counter() - start) * 1000.0, 4), output


def cache_files(cache_dir: Path) -> list[dict[str, Any]]:
    if not cache_dir.exists():
        return []
    files = []
    for path in sorted(p for p in cache_dir.rglob("*") if p.is_file()):
        files.append({
            "path": relpath(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return files


def make_session(ort: Any, onnx_path: Path, provider_options: dict[str, Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    session = ort.InferenceSession(str(onnx_path), providers=[("TensorrtExecutionProvider", provider_options), "CUDAExecutionProvider", "CPUExecutionProvider"])
    return session, round((time.perf_counter() - start) * 1000.0, 4)


def run_phase(ort: Any, phase: str, onnx_path: Path, inputs: np.ndarray, provider_options: dict[str, Any], repeat: int, warmup: int) -> dict[str, Any]:
    session, session_create_ms = make_session(ort, onnx_path, provider_options)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    def work() -> np.ndarray:
        return session.run([output_name], {input_name: inputs})[0]

    first_ms, first_output = first_run_ms(work)
    latency, output = timed_repeats(work, repeat, warmup)
    top_indices = np.argsort(output[0])[-5:][::-1].tolist()
    return {
        "phase": phase,
        "session_create_ms": session_create_ms,
        "first_run_ms": first_ms,
        "session_providers": session.get_providers(),
        "input_name": input_name,
        "output_name": output_name,
        "latency": latency,
        "output_summary": {
            "first_run_top_index": int(np.argmax(first_output[0])),
            "top_indices": top_indices,
            "top_values": [round(float(output[0][index]), 6) for index in top_indices],
        },
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    cold = result["phases"]["cold_build"]
    warm = result["phases"]["warm_cache"]
    cache = result["cache"]
    return "\n".join([
        "# ONNX Runtime TensorRT EP Engine Cache Report", "",
        "> ONNX Runtime TensorRT EP provider option과 engine cache 조건을 명시하고, cold build와 warm cache 실행을 분리한 evidence입니다.", "",
        "## Run Information", "", "| Field | Value |", "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['conda_env']}` |",
        f"| ONNX Runtime | {meta['onnxruntime']['version']} |",
        f"| Available providers | `{meta['onnxruntime']['available_providers']}` |",
        f"| Result JSON | `{meta['result_json']}` |", "",
        "## Provider Options", "", "| Option | Value |", "|---|---|",
        *[f"| `{key}` | `{value}` |" for key, value in result["provider_options"].items()], "",
        "## Cache Artifacts", "", "| Field | Value |", "|---|---|",
        f"| Cache path | `{cache['cache_path']}` |",
        f"| Cache prefix | `{cache['cache_prefix']}` |",
        f"| Cache file count | {len(cache['files'])} |", "",
        "## Phase Results", "", "| Phase | Session create ms | First run ms | Mean ms | P95 ms | Session providers |",
        "|---|---:|---:|---:|---:|---|",
        f"| Cold build | {cold['session_create_ms']} | {cold['first_run_ms']} | {cold['latency']['mean_ms']} | {cold['latency']['p95_ms']} | `{cold['session_providers']}` |",
        f"| Warm cache | {warm['session_create_ms']} | {warm['first_run_ms']} | {warm['latency']['mean_ms']} | {warm['latency']['p95_ms']} | `{warm['session_providers']}` |", "",
        "## Interpretation", "",
        "- Cold build clears the cache directory before session creation.",
        "- Warm cache reuses the same provider options and cache directory after cold build has generated cache artifacts.",
        "- Session creation time captures TensorRT EP build/cache load cost; repeated latency captures `session.run` after session creation.",
        "- This remains runtime/provider/cache evidence, not deployment readiness or accuracy evidence.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark ONNX Runtime TensorRT EP engine cache behavior.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--onnx", type=Path, default=Path("models/resnet18_random_seed42_opset17.onnx"))
    parser.add_argument("--tensorrt-json", type=Path, default=Path("results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path("artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32"))
    parser.add_argument("--cache-prefix", default="resnet18_fp32")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clear-cache", action="store_true")
    args = parser.parse_args()

    import onnxruntime as ort

    if args.clear_cache and args.cache_dir.exists():
        shutil.rmtree(args.cache_dir)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    provider_options: dict[str, Any] = {
        "trt_engine_cache_enable": True,
        "trt_engine_cache_path": str(args.cache_dir),
        "trt_engine_cache_prefix": args.cache_prefix,
        "trt_fp16_enable": False,
    }
    input_shape = [1, 3, 224, 224]
    rng = np.random.default_rng(args.seed)
    inputs = rng.random(input_shape, dtype=np.float32)

    cold = run_phase(ort, "cold_build", args.onnx, inputs, provider_options, args.repeat, args.warmup)
    cache_after_cold = cache_files(args.cache_dir)
    warm = run_phase(ort, "warm_cache", args.onnx, inputs, provider_options, args.repeat, args.warmup)
    cache_after_warm = cache_files(args.cache_dir)

    model_meta = load_tensorrt_model_meta(args.tensorrt_json)
    onnx_sha = sha256_file(args.onnx)
    payload = {
        "metadata": {
            "schema_version": "onnxruntime-tensorrt-cache-bench-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": Path(sys.executable).name,
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "onnxruntime": {"version": ort.__version__, "available_providers": ort.get_available_providers()},
            "result_json": relpath(args.output),
        },
        "result": {
            "task": "onnxruntime_tensorrt_engine_cache_bench",
            "framework": "onnxruntime",
            "backend": "TensorrtExecutionProvider",
            "precision": "fp32",
            "model": {
                "architecture": model_meta.get("architecture", "resnet18"),
                "weights": model_meta.get("weights", "random_seeded_weights_no_pretrained_accuracy_claim"),
                "state_dict_sha256": model_meta.get("state_dict_sha256", ""),
                "onnx_path": str(args.onnx),
                "onnx_sha256": onnx_sha,
                "onnx_sha256_matches_tensorrt_source": bool(model_meta.get("onnx_sha256_from_tensorrt")) and model_meta.get("onnx_sha256_from_tensorrt") == onnx_sha,
            },
            "input": {"source": "synthetic_random_numpy_array", "shape": input_shape, "dtype": "float32", "seed": args.seed},
            "provider_options": {key: (relpath(Path(value)) if key == "trt_engine_cache_path" else value) for key, value in provider_options.items()},
            "runtime": {"warmup": args.warmup, "repeat": args.repeat, "timing": "session_create_first_run_and_repeated_session_run"},
            "cache": {"cache_path": relpath(args.cache_dir), "cache_prefix": args.cache_prefix, "files_after_cold_build": cache_after_cold, "files": cache_after_warm},
            "phases": {"cold_build": cold, "warm_cache": warm},
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(build_report(payload), encoding="utf-8")
    print(args.output)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
