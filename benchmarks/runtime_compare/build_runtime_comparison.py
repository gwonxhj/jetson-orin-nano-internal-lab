#!/usr/bin/env python3
"""Build runtime comparison evidence from PyTorch, ONNX Runtime, and TensorRT smoke JSON files."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def latest_file(pattern: str) -> Path:
    matches = sorted(Path().glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no files matched {pattern}")
    return matches[-1]


def latest_optional_file(pattern: str) -> Path | None:
    matches = sorted(Path().glob(pattern))
    return matches[-1] if matches else None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pytorch_runtime(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = payload["result"]
    latency = result["latency"]
    return {
        "name": "pytorch_cuda",
        "framework": result["framework"],
        "backend": result["backend"],
        "precision": result["precision"],
        "model_hash": result["model"]["state_dict_sha256"],
        "input_shape": result["input"]["shape"],
        "warmup": result["runtime"]["warmup"],
        "repeat_or_iterations": result["runtime"]["repeat"],
        "latency_ms": {"mean": latency["mean_ms"], "p50": latency["p50_ms"], "p95": latency["p95_ms"], "p99": latency["p99_ms"], "min": latency["min_ms"], "max": latency["max_ms"]},
        "throughput_qps": None,
        "source_json": str(path),
    }


def onnxruntime_runtime(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = payload["result"]
    latency = result["latency"]
    meta = payload["metadata"]
    return {
        "name": "onnxruntime_cpu",
        "framework": result["framework"],
        "backend": result["provider"],
        "precision": result["precision"],
        "model_hash": result["model"].get("state_dict_sha256", ""),
        "input_shape": result["input"]["shape"],
        "warmup": result["runtime"]["warmup"],
        "repeat_or_iterations": result["runtime"]["repeat"],
        "latency_ms": {"mean": latency["mean_ms"], "p50": latency["p50_ms"], "p95": latency["p95_ms"], "p99": latency["p99_ms"], "min": latency["min_ms"], "max": latency["max_ms"]},
        "throughput_qps": None,
        "source_json": str(path),
        "onnx_path": result["model"].get("onnx_path"),
        "onnx_sha256": result["model"].get("onnx_sha256"),
        "provider_status": meta.get("onnxruntime", {}).get("provider_status", {}),
    }


def tensorrt_runtime(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    result = payload["result"]
    latency = result["metrics"]["latency_ms"]
    return {
        "name": "tensorrt_trtexec",
        "framework": result["runtime"],
        "backend": "trtexec",
        "precision": result["precision"],
        "model_hash": result["model"]["state_dict_sha256"],
        "input_shape": result["input_shape"],
        "warmup": f"{result['protocol']['warmup_ms']}ms",
        "repeat_or_iterations": result["protocol"]["iterations"],
        "latency_ms": {"mean": latency["mean"], "p50": latency["median"], "p95": latency["p95"], "p99": latency["p99"], "min": latency["min"], "max": latency["max"]},
        "throughput_qps": result["metrics"].get("throughput_qps"),
        "source_json": str(path),
        "engine_path": result["artifacts"]["engine_path"],
        "engine_sha256": result["artifacts"]["engine_sha256"],
        "onnx_path": result["artifacts"]["onnx_path"],
        "onnx_sha256": result["artifacts"]["onnx_sha256"],
    }


def ratio(a: dict[str, Any], b: dict[str, Any], field: str = "mean") -> float:
    return round(a["latency_ms"][field] / b["latency_ms"][field], 4)


def build_payload(pytorch_path: Path, tensorrt_path: Path, onnxruntime_path: Path | None = None) -> dict[str, Any]:
    pytorch_payload = load_json(pytorch_path)
    tensorrt_payload = load_json(tensorrt_path)
    runtimes = [pytorch_runtime(pytorch_path, pytorch_payload)]
    ort_runtime = None
    if onnxruntime_path is not None:
        ort_runtime = onnxruntime_runtime(onnxruntime_path, load_json(onnxruntime_path))
        runtimes.append(ort_runtime)
    trt_runtime = tensorrt_runtime(tensorrt_path, tensorrt_payload)
    runtimes.append(trt_runtime)

    hashes = [runtime.get("model_hash") for runtime in runtimes if runtime.get("model_hash")]
    shapes = [runtime["input_shape"] for runtime in runtimes]
    precisions = [runtime["precision"] for runtime in runtimes]
    same_hash = len(set(hashes)) == 1 if hashes else False
    same_shape = all(shape == shapes[0] for shape in shapes)
    same_precision = len(set(precisions)) == 1
    same_prepost = True
    for payload in [pytorch_payload, tensorrt_payload] + ([load_json(onnxruntime_path)] if onnxruntime_path is not None else []):
        result = payload["result"]
        if result.get("input", {}).get("preprocessing_included") not in (False, None):
            same_prepost = False
        post = result.get("input", {}).get("postprocessing_included", result.get("protocol", {}).get("postprocessing_included"))
        if post not in (False, None, "top5_only", "top5_only_after_timing"):
            same_prepost = False

    ratios: dict[str, Any] = {
        "mean_latency_pytorch_over_tensorrt": ratio(runtimes[0], trt_runtime),
        "p95_latency_pytorch_over_tensorrt": ratio(runtimes[0], trt_runtime, "p95"),
    }
    if ort_runtime is not None:
        ratios.update({
            "mean_latency_pytorch_over_onnxruntime": ratio(runtimes[0], ort_runtime),
            "p95_latency_pytorch_over_onnxruntime": ratio(runtimes[0], ort_runtime, "p95"),
            "mean_latency_onnxruntime_over_tensorrt": ratio(ort_runtime, trt_runtime),
            "p95_latency_onnxruntime_over_tensorrt": ratio(ort_runtime, trt_runtime, "p95"),
        })

    comparison_name = "resnet18_pytorch_cuda_fp32_vs_tensorrt_fp16"
    notes = [
        "PyTorch uses CUDA FP32 eager execution while TensorRT uses FP16 trtexec engine execution.",
        "The model hash and input shape match, but precision and runtime differ.",
        "Synthetic input is used; preprocessing and accuracy are outside this comparison.",
        "PyTorch top-5 output summary is computed after timed inference and is not included in latency.",
    ]
    source_files = {"pytorch": str(pytorch_path), "tensorrt": str(tensorrt_path)}
    if ort_runtime is not None and onnxruntime_path is not None:
        comparison_name = "resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_tensorrt_fp16"
        source_files["onnxruntime"] = str(onnxruntime_path)
        provider_status = ort_runtime.get("provider_status", {})
        notes.extend([
            "ONNX Runtime CPUExecutionProvider is included as a third runtime using the same ONNX artifact.",
            f"ONNX Runtime CUDAExecutionProvider available: {provider_status.get('cuda_available', False)}.",
            "ONNX Runtime CPU and PyTorch CUDA are different providers, so their latency is not a direct regression comparison.",
        ])

    return {
        "metadata": {
            "schema_version": "runtime-compare-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": "python3",
            "python_version": platform.python_version(),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "source_files": source_files,
        },
        "result": {
            "comparison_name": comparison_name,
            "model": "resnet18",
            "input_shape": shapes[0],
            "comparability": {
                "same_model_hash": same_hash,
                "same_input_shape": same_shape,
                "same_precision": same_precision,
                "same_preprocessing_postprocessing_scope": same_prepost,
                "verdict": "runtime_comparison_not_direct_regression",
                "notes": notes,
            },
            "runtimes": runtimes,
            "ratios": ratios,
        },
    }


def runtime_label(runtime: dict[str, Any]) -> str:
    return {"pytorch_cuda": "PyTorch CUDA", "onnxruntime_cpu": "ONNX Runtime CPU", "tensorrt_trtexec": "TensorRT trtexec"}.get(runtime["name"], runtime["name"])


def write_markdown(payload: dict[str, Any], output: Path) -> None:
    result = payload["result"]
    meta = payload["metadata"]
    comp = result["comparability"]
    lines = [
        "# Runtime Comparison Report",
        "",
        "> ResNet18 PyTorch CUDA FP32, ONNX Runtime CPU FP32, TensorRT FP16 smoke 결과를 비교합니다.",
        "> backend/provider/precision이 다르면 direct regression이 아니라 runtime comparison evidence입니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Power mode | {meta['power_mode'].get('stdout', '').replace(chr(10), '; ')} |",
        f"| Git commit | {meta['git_commit'].get('stdout', 'unknown')} |",
    ]
    for label, source in meta["source_files"].items():
        lines.append(f"| {label} source | `{source}` |")
    lines.extend([
        "",
        "## Comparability",
        "",
        "| Check | Value |",
        "|---|---:|",
        f"| Same model hash | {comp['same_model_hash']} |",
        f"| Same input shape | {comp['same_input_shape']} |",
        f"| Same precision | {comp['same_precision']} |",
        f"| Same pre/post scope | {comp['same_preprocessing_postprocessing_scope']} |",
        f"| Verdict | `{comp['verdict']}` |",
        "",
        "## Runtime Results",
        "",
        "| Runtime | Backend / Provider | Precision | Input shape | Mean ms | P95 ms | P99 ms | Throughput qps |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ])
    for runtime in result["runtimes"]:
        throughput = runtime["throughput_qps"] if runtime["throughput_qps"] is not None else "n/a"
        lines.append(
            f"| {runtime_label(runtime)} | {runtime['backend']} | {runtime['precision']} | {runtime['input_shape']} | "
            f"{runtime['latency_ms']['mean']} | {runtime['latency_ms']['p95']} | {runtime['latency_ms']['p99']} | {throughput} |"
        )
    lines.extend(["", "## Ratios", "", "| Ratio | Value |", "|---|---:|"])
    for key, value in result["ratios"].items():
        lines.append(f"| {key} | {value}x |")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in comp["notes"])
    lines.extend([
        "- TensorRT engine and ONNX hashes are preserved in the comparison JSON.",
        "- Synthetic input is used, so this is runtime evidence, not model quality evidence.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PyTorch/ONNX Runtime/TensorRT runtime comparison evidence.")
    parser.add_argument("--pytorch", type=Path, default=None)
    parser.add_argument("--onnxruntime", type=Path, default=None)
    parser.add_argument("--tensorrt", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    pytorch_path = args.pytorch or latest_file("results/inference/pytorch_resnet18_*.json")
    onnxruntime_path = args.onnxruntime or latest_optional_file("results/inference/onnxruntime_resnet18_*.json")
    tensorrt_path = args.tensorrt or latest_file("results/tensorrt/resnet18_fp16_trtexec_*.json")
    payload = build_payload(pytorch_path, tensorrt_path, onnxruntime_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown)
    print(args.output)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
