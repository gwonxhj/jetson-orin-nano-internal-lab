#!/usr/bin/env python3
"""Tiny local LLM text-generation smoke runner.

This runner is intentionally safe by default:
- it does not install packages;
- it does not download model weights unless --allow-download is set;
- missing dependency/model states are written as evidence instead of mutating
  the current Jetson environment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MODEL_ALIASES = {
    "tiny-gpt2": "sshleifer/tiny-gpt2",
    "distilgpt2": "distilgpt2",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def display_path(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        text = str(path_obj)
        home = str(Path.home())
        if text.startswith(home):
            return text.replace(home, "[home]", 1)
        return text


def run_command(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
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


def package_version(module_name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {"available": False, "version": ""}
    try:
        module = __import__(module_name)
        return {"available": True, "version": getattr(module, "__version__", "unknown")}
    except Exception as exc:
        return {"available": False, "version": "", "error": repr(exc)}


def detect_torch() -> dict[str, Any]:
    try:
        import torch

        return {
            "available": True,
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": torch.version.cuda,
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        }
    except Exception as exc:
        return {"available": False, "error": repr(exc)}


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
        "samples_ms": [round(value, 4) for value in samples_ms],
        "count": len(samples_ms),
        "mean_ms": round(statistics.fmean(samples_ms), 4),
        "min_ms": round(min(samples_ms), 4),
        "p50_ms": round(percentile(0.50), 4),
        "p95_ms": round(percentile(0.95), 4),
        "p99_ms": round(percentile(0.99), 4),
        "max_ms": round(max(samples_ms), 4),
    }


def timed_repeats(fn: Callable[[], Any], repeat: int, warmup: int, sync_cuda: Callable[[], None]) -> tuple[dict[str, Any], Any]:
    last_value: Any = None
    for _ in range(warmup):
        last_value = fn()
        sync_cuda()
    samples: list[float] = []
    for _ in range(repeat):
        sync_cuda()
        start = time.perf_counter()
        last_value = fn()
        sync_cuda()
        samples.append((time.perf_counter() - start) * 1000.0)
    return summarize(samples), last_value


def resolve_device(device_arg: str, torch_info: dict[str, Any]) -> str:
    if device_arg != "auto":
        return device_arg
    if torch_info.get("cuda_available"):
        return "cuda"
    return "cpu"


def base_payload(args: argparse.Namespace, model_id: str, torch_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": {
            "schema_version": "llm-text-generation-smoke-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "package": {
                "transformers": package_version("transformers"),
                "torch": torch_info,
            },
            "isolation": {
                "target_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
                "existing_env_modified": False,
                "install_command_executed": False,
                "download_allowed": bool(args.allow_download),
                "offline_only": not bool(args.allow_download),
            },
            "tegrastats_log": display_path(args.tegrastats_log) if args.tegrastats_log else "",
        },
        "result": {
            "task": "llm_text_generation_smoke",
            "framework": "transformers",
            "model": {
                "alias": args.model_alias,
                "id": model_id,
            },
            "prompt": args.prompt,
            "status": "not_run",
            "success": False,
            "failure_reason": "",
            "runtime": {
                "device": "unresolved",
                "precision": "framework_default",
                "warmup": args.warmup,
                "repeat": args.repeat,
                "max_new_tokens": args.max_new_tokens,
                "download_allowed": bool(args.allow_download),
            },
            "latency_ms": {},
            "generation": {
                "text": "",
                "prompt_token_count": 0,
                "generated_token_count": 0,
            },
            "interpretation": {
                "path_smoke_only": True,
                "quality_claim": False,
                "deployment_ready_claim": False,
            },
        },
    }


def mark_unavailable(payload: dict[str, Any], status: str, reason: str, device: str = "unavailable") -> dict[str, Any]:
    payload["result"]["status"] = status
    payload["result"]["success"] = False
    payload["result"]["failure_reason"] = reason
    payload["result"]["runtime"]["device"] = device
    return payload


def run_generation(args: argparse.Namespace, model_id: str, torch_info: dict[str, Any]) -> dict[str, Any]:
    payload = base_payload(args, model_id, torch_info)
    if not payload["metadata"]["package"]["transformers"]["available"]:
        return mark_unavailable(payload, "dependency_missing", "transformers is not installed in the active environment")
    if not torch_info.get("available"):
        return mark_unavailable(payload, "dependency_missing", "torch is not importable in the active environment")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = resolve_device(args.device, torch_info)
    payload["result"]["runtime"]["device"] = device
    local_files_only = not args.allow_download
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=local_files_only)
        model = AutoModelForCausalLM.from_pretrained(model_id, local_files_only=local_files_only)
    except Exception as exc:
        if local_files_only:
            return mark_unavailable(payload, "model_missing", f"model/tokenizer not available in local cache: {exc}", device=device)
        return mark_unavailable(payload, "failed", f"model load failed: {exc}", device=device)

    model.eval()
    model.to(device)
    if device == "cuda":
        payload["result"]["runtime"]["precision"] = "fp32_cuda_framework_default"
    else:
        payload["result"]["runtime"]["precision"] = "fp32_cpu_framework_default"

    inputs = tokenizer(args.prompt, return_tensors="pt")
    inputs = {name: value.to(device) for name, value in inputs.items()}

    def sync_cuda() -> None:
        if device == "cuda":
            torch.cuda.synchronize()

    def generate_once() -> Any:
        with torch.inference_mode():
            return model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, pad_token_id=tokenizer.eos_token_id)

    latency, output_ids = timed_repeats(generate_once, args.repeat, args.warmup, sync_cuda)
    generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    prompt_token_count = int(inputs["input_ids"].shape[-1])
    generated_token_count = int(output_ids.shape[-1] - prompt_token_count)

    payload["result"]["status"] = "succeeded"
    payload["result"]["success"] = True
    payload["result"]["failure_reason"] = ""
    payload["result"]["latency_ms"] = latency
    payload["result"]["generation"] = {
        "text": generated_text,
        "prompt_token_count": prompt_token_count,
        "generated_token_count": generated_token_count,
    }
    return payload


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    latency = result["latency_ms"]
    generation_text = result["generation"]["text"] or "(not generated)"
    return "\n".join([
        "# LLM Text Generation Smoke Report",
        "",
        "> Tiny local text-generation path를 Jetson에서 격리 검증하기 위한 smoke report입니다.",
        "> 이 결과는 model quality나 deployment readiness를 주장하지 않습니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['conda_env']}` |",
        f"| Transformers available | {meta['package']['transformers']['available']} |",
        f"| Torch CUDA available | {meta['package']['torch'].get('cuda_available', False)} |",
        f"| Model | `{result['model']['id']}` |",
        f"| Device | `{result['runtime']['device']}` |",
        f"| Download allowed | {meta['isolation']['download_allowed']} |",
        f"| Offline only | {meta['isolation']['offline_only']} |",
        f"| Status | `{result['status']}` |",
        f"| Failure reason | `{result['failure_reason'] or 'none'}` |",
        "",
        "## Runtime",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Warmup | {result['runtime']['warmup']} |",
        f"| Repeat | {result['runtime']['repeat']} |",
        f"| Max new tokens | {result['runtime']['max_new_tokens']} |",
        f"| Mean ms | {latency.get('mean_ms', 'not measured')} |",
        f"| P95 ms | {latency.get('p95_ms', 'not measured')} |",
        "",
        "## Prompt",
        "",
        "```text",
        result["prompt"],
        "```",
        "",
        "## Generated Text Preview",
        "",
        "```text",
        generation_text,
        "```",
        "",
        "## Interpretation",
        "",
        "- This is path evidence for an isolated local LLM smoke, not a benchmark claiming deployment readiness.",
        "- `dependency_missing` or `model_missing` is an expected safe state before the isolated `llm_env` is created or model cache policy is approved.",
        "- Compare latency only with matching model, device, precision, warmup/repeat, and download/cache state.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tiny LLM text-generation smoke.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model-alias", default="tiny-gpt2", choices=sorted(MODEL_ALIASES))
    parser.add_argument("--model-id", default="")
    parser.add_argument("--prompt", default="Jetson edge AI")
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    model_id = args.model_id or MODEL_ALIASES[args.model_alias]
    torch_info = detect_torch()
    payload = run_generation(args, model_id, torch_info)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(build_report(payload), encoding="utf-8")
    print(args.output)
    print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
