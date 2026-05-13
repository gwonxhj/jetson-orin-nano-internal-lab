#!/usr/bin/env python3
"""Build runtime comparison evidence from PyTorch and TensorRT smoke JSON files."""

from __future__ import annotations

import argparse
import json
import platform
import socket
import subprocess
import sys
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


def latest_file(pattern: str) -> Path:
    matches = sorted(Path().glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no files matched {pattern}")
    return matches[-1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload(pytorch_path: Path, tensorrt_path: Path) -> dict[str, Any]:
    pytorch = load_json(pytorch_path)
    tensorrt = load_json(tensorrt_path)
    pr = pytorch["result"]
    tr = tensorrt["result"]
    pt_latency = pr["latency"]
    trt_latency = tr["metrics"]["latency_ms"]
    same_hash = pr["model"]["state_dict_sha256"] == tr["model"]["state_dict_sha256"]
    same_shape = pr["input"]["shape"] == tr["input_shape"]
    same_precision = pr["precision"] == tr["precision"]
    same_prepost = (
        pr["input"].get("preprocessing_included") is False
        and tr["protocol"].get("preprocessing_included") is False
        and pr["input"].get("postprocessing_included") in (False, "top5_only")
        and tr["protocol"].get("postprocessing_included") is False
    )
    mean_ratio = pt_latency["mean_ms"] / trt_latency["mean"]
    p95_ratio = pt_latency["p95_ms"] / trt_latency["p95"]

    return {
        "metadata": {
            "schema_version": "runtime-compare-v1",
            "generated_at": now_iso(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": run_command(["git", "status", "--short", "--branch"]),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "source_files": {
                "pytorch": str(pytorch_path),
                "tensorrt": str(tensorrt_path),
            },
        },
        "result": {
            "comparison_name": "resnet18_pytorch_cuda_fp32_vs_tensorrt_fp16",
            "model": "resnet18",
            "input_shape": pr["input"]["shape"],
            "comparability": {
                "same_model_hash": same_hash,
                "same_input_shape": same_shape,
                "same_precision": same_precision,
                "same_preprocessing_postprocessing_scope": same_prepost,
                "verdict": "runtime_comparison_not_direct_regression",
                "notes": [
                    "PyTorch uses CUDA FP32 eager execution while TensorRT uses FP16 trtexec engine execution.",
                    "The model hash and input shape match, but precision and runtime differ.",
                    "Synthetic input is used; preprocessing and accuracy are outside this comparison.",
                    "PyTorch top-5 output summary is computed after timed inference and is not included in latency.",
                ],
            },
            "runtimes": [
                {
                    "name": "pytorch_cuda",
                    "framework": pr["framework"],
                    "backend": pr["backend"],
                    "precision": pr["precision"],
                    "model_hash": pr["model"]["state_dict_sha256"],
                    "input_shape": pr["input"]["shape"],
                    "warmup": pr["runtime"]["warmup"],
                    "repeat_or_iterations": pr["runtime"]["repeat"],
                    "latency_ms": {
                        "mean": pt_latency["mean_ms"],
                        "p50": pt_latency["p50_ms"],
                        "p95": pt_latency["p95_ms"],
                        "p99": pt_latency["p99_ms"],
                        "min": pt_latency["min_ms"],
                        "max": pt_latency["max_ms"],
                    },
                    "throughput_qps": None,
                    "source_json": str(pytorch_path),
                },
                {
                    "name": "tensorrt_trtexec",
                    "framework": tr["runtime"],
                    "backend": "trtexec",
                    "precision": tr["precision"],
                    "model_hash": tr["model"]["state_dict_sha256"],
                    "input_shape": tr["input_shape"],
                    "warmup": f"{tr['protocol']['warmup_ms']}ms",
                    "repeat_or_iterations": tr["protocol"]["iterations"],
                    "latency_ms": {
                        "mean": trt_latency["mean"],
                        "p50": trt_latency["median"],
                        "p95": trt_latency["p95"],
                        "p99": trt_latency["p99"],
                        "min": trt_latency["min"],
                        "max": trt_latency["max"],
                    },
                    "throughput_qps": tr["metrics"].get("throughput_qps"),
                    "source_json": str(tensorrt_path),
                    "engine_path": tr["artifacts"]["engine_path"],
                    "engine_sha256": tr["artifacts"]["engine_sha256"],
                    "onnx_path": tr["artifacts"]["onnx_path"],
                    "onnx_sha256": tr["artifacts"]["onnx_sha256"],
                },
            ],
            "ratios": {
                "mean_latency_pytorch_over_tensorrt": round(mean_ratio, 4),
                "p95_latency_pytorch_over_tensorrt": round(p95_ratio, 4),
            },
        },
    }


def write_markdown(payload: dict[str, Any], output: Path) -> None:
    result = payload["result"]
    meta = payload["metadata"]
    pt, trt = result["runtimes"]
    comp = result["comparability"]
    lines = [
        "# Runtime Comparison Report",
        "",
        "> ResNet18 PyTorch CUDA FP32와 TensorRT FP16 smoke 결과를 비교합니다.",
        "> precision/runtime이 다르므로 direct regression이 아니라 runtime comparison evidence입니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Power mode | {meta['power_mode'].get('stdout', '').replace(chr(10), '; ')} |",
        f"| Git commit | {meta['git_commit'].get('stdout', 'unknown')} |",
        f"| PyTorch source | `{meta['source_files']['pytorch']}` |",
        f"| TensorRT source | `{meta['source_files']['tensorrt']}` |",
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
        "| Runtime | Precision | Input shape | Mean ms | P95 ms | P99 ms | Throughput qps |",
        "|---|---|---|---:|---:|---:|---:|",
        f"| PyTorch CUDA | {pt['precision']} | {pt['input_shape']} | {pt['latency_ms']['mean']} | {pt['latency_ms']['p95']} | {pt['latency_ms']['p99']} | n/a |",
        f"| TensorRT trtexec | {trt['precision']} | {trt['input_shape']} | {trt['latency_ms']['mean']} | {trt['latency_ms']['p95']} | {trt['latency_ms']['p99']} | {trt['throughput_qps']} |",
        "",
        "## Ratios",
        "",
        "| Ratio | Value |",
        "|---|---:|",
        f"| Mean latency PyTorch / TensorRT | {result['ratios']['mean_latency_pytorch_over_tensorrt']}x |",
        f"| P95 latency PyTorch / TensorRT | {result['ratios']['p95_latency_pytorch_over_tensorrt']}x |",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in comp["notes"])
    lines.extend([
        "- TensorRT engine and ONNX hashes are preserved in the comparison JSON.",
        "- Synthetic input is used, so this is runtime evidence, not model quality evidence.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PyTorch/TensorRT runtime comparison evidence.")
    parser.add_argument("--pytorch", type=Path, default=None)
    parser.add_argument("--tensorrt", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    pytorch_path = args.pytorch or latest_file("results/inference/pytorch_resnet18_*.json")
    tensorrt_path = args.tensorrt or latest_file("results/tensorrt/resnet18_fp16_trtexec_*.json")
    payload = build_payload(pytorch_path, tensorrt_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown)
    print(args.output)
    print(args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
