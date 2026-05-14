#!/usr/bin/env python3
"""Probe isolated LLM environment candidates without installing packages."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SENSITIVE_REPLACEMENTS = (
    (str(Path.home()), "[home]"),
    (Path.home().name, "jetson-user"),
    (platform.node().split(".", 1)[0], "jetson-host"),
)


@dataclass(frozen=True)
class Candidate:
    name: str
    backend: str
    package: str
    install_spec: str
    env_strategy: str
    runtime_engine: str
    model_candidate: str
    expected_device_path: str
    trust_level: str
    notes: str


CANDIDATES = [
    Candidate(
        name="transformers_tiny_gpt2_clone_yolo",
        backend="transformers",
        package="transformers",
        install_spec="transformers accelerate safetensors sentencepiece",
        env_strategy="conda clone yolo_env, then pip install transformers stack inside llm_env",
        runtime_engine="PyTorch",
        model_candidate="sshleifer/tiny-gpt2",
        expected_device_path="cuda if cloned torch remains usable, cpu fallback otherwise",
        trust_level="upstream_open_source_package_and_huggingface_model",
        notes="Best first LLM candidate because it reuses the known Jetson PyTorch CUDA stack and keeps model size tiny.",
    ),
    Candidate(
        name="transformers_distilgpt2_followup",
        backend="transformers",
        package="transformers",
        install_spec="transformers accelerate safetensors sentencepiece",
        env_strategy="reuse llm_env after tiny-gpt2 succeeds",
        runtime_engine="PyTorch",
        model_candidate="distilgpt2",
        expected_device_path="cuda if memory and cache allow, cpu fallback otherwise",
        trust_level="upstream_open_source_package_and_huggingface_model",
        notes="Useful follow-up for a less toy model, but it should not be the first smoke because model download/cache is larger.",
    ),
    Candidate(
        name="llama_cpp_python_followup",
        backend="llama-cpp-python",
        package="llama-cpp-python",
        install_spec="llama-cpp-python",
        env_strategy="separate llm_env variant after transformers smoke succeeds",
        runtime_engine="llama.cpp",
        model_candidate="small GGUF model candidate to be selected later",
        expected_device_path="cpu first; CUDA build support must be proven separately on Jetson",
        trust_level="native_extension_requires_build_review",
        notes="Potential local LLM runtime follow-up, but native build and GGUF model provenance need separate evidence.",
    ),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sanitize_text(value: str) -> str:
    sanitized = value
    for needle, replacement in SENSITIVE_REPLACEMENTS:
        sanitized = sanitized.replace(needle, replacement)
    return sanitized


def sanitize_command(command: list[str]) -> list[str]:
    return [sanitize_text(part) for part in command]


def run_command(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {
            "command": sanitize_command(command),
            "exit_code": completed.returncode,
            "stdout": sanitize_text(completed.stdout.strip()),
            "stderr": sanitize_text(completed.stderr.strip()),
        }
    except Exception as exc:
        return {"command": sanitize_command(command), "error": sanitize_text(repr(exc))}


def package_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


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
        return {"available": False, "error": sanitize_text(repr(exc))}


def conda_env_exists(name: str) -> bool:
    conda = run_command(["conda", "env", "list"])
    return any(line.split()[0] == name for line in conda.get("stdout", "").splitlines() if line and not line.startswith("#"))


def detect_environment(target_env: str) -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_executable": "python3 (current env)",
        "python_tag": f"cp{sys.version_info.major}{sys.version_info.minor}",
        "machine": platform.machine(),
        "platform": sanitize_text(platform.platform()),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "target_env": target_env,
        "target_env_exists": conda_env_exists(target_env),
        "torch": detect_torch(),
        "current_packages": {
            "transformers": package_available("transformers"),
            "accelerate": package_available("accelerate"),
            "safetensors": package_available("safetensors"),
            "sentencepiece": package_available("sentencepiece"),
            "llama_cpp": package_available("llama_cpp"),
        },
    }


def evaluate_candidate(candidate: Candidate, env: dict[str, Any]) -> dict[str, Any]:
    python_matches = env["python_tag"] == "cp310"
    platform_matches = env["machine"] == "aarch64"
    torch_cuda_available = bool(env["torch"].get("cuda_available"))
    target_free = not env["target_env_exists"]
    transformers_not_installed = not env["current_packages"]["transformers"]
    if candidate.name == "transformers_tiny_gpt2_clone_yolo":
        if python_matches and platform_matches and torch_cuda_available and target_free:
            verdict = "recommended_first_isolated_candidate"
        elif python_matches and platform_matches and torch_cuda_available and env["target_env_exists"]:
            verdict = "isolated_env_exists_validate_or_reuse"
        else:
            verdict = "requires_review"
    elif candidate.backend == "transformers":
        verdict = "followup_after_tiny_smoke" if python_matches and platform_matches else "requires_review"
    else:
        verdict = "followup_requires_native_build_review"
    return {
        "name": candidate.name,
        "backend": candidate.backend,
        "package": candidate.package,
        "install_spec": candidate.install_spec,
        "env_strategy": candidate.env_strategy,
        "runtime_engine": candidate.runtime_engine,
        "model_candidate": candidate.model_candidate,
        "expected_device_path": candidate.expected_device_path,
        "trust_level": candidate.trust_level,
        "notes": candidate.notes,
        "checks": {
            "python_cp310": python_matches,
            "platform_aarch64": platform_matches,
            "torch_cuda_available_in_source_env": torch_cuda_available,
            "target_env_free": target_free,
            "current_transformers_not_installed": transformers_not_installed,
        },
        "candidate_verdict": verdict,
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    env = meta["environment"]
    rows = [
        f"| {item['backend']} | `{item['model_candidate']}` | `{item['install_spec']}` | {item['runtime_engine']} | `{item['candidate_verdict']}` |"
        for item in result["candidates"]
    ]
    if env["target_env_exists"]:
        recommended_flow = [
            "1. Keep `yolo_env` unchanged.",
            f"2. Reuse existing `{env['target_env']}` for tiny text-generation smoke validation.",
            f"3. Run `LLM_ALLOW_DOWNLOAD=1 conda run -n {env['target_env']} bash scripts/run_llm_smoke.sh tiny-gpt2` when model download/cache is allowed.",
            "4. Treat `sshleifer/tiny-gpt2` as path smoke only; do not claim model quality or deployment readiness.",
        ]
    else:
        recommended_flow = [
            "1. Keep `yolo_env` unchanged.",
            "2. Run `bash scripts/create_llm_env.sh` first and review the plan.",
            "3. Create the isolated env only with `bash scripts/create_llm_env.sh --execute`.",
            f"4. Use `conda run -n {env['target_env']} bash scripts/run_llm_smoke.sh tiny-gpt2` after reviewing model download/cache policy.",
            "5. Treat `sshleifer/tiny-gpt2` as path smoke only; do not claim model quality or deployment readiness.",
        ]
    return "\n".join([
        "# LLM Env Candidate Probe",
        "",
        "> 기존 `yolo_env`를 변경하지 않고 tiny text-generation smoke로 넘어가기 위한 격리 env 후보 검증입니다.",
        "",
        "## Environment",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Current conda env | `{env['conda_env']}` |",
        f"| Target env | `{env['target_env']}` exists: {env['target_env_exists']} |",
        f"| Python tag | `{env['python_tag']}` |",
        f"| Machine | `{env['machine']}` |",
        f"| Torch CUDA available | {env['torch'].get('cuda_available', False)} |",
        f"| Current transformers installed | {env['current_packages']['transformers']} |",
        f"| Result JSON | `{meta['result_json']}` |",
        "",
        "## Candidate Summary",
        "",
        "| Backend | Model candidate | Install spec | Runtime engine | Verdict |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "## Recommended Flow",
        "",
        *recommended_flow,
        "",
        "## Notes",
        "",
        "- This probe does not install packages, create envs, or download model weights.",
        "- The first candidate is intentionally tiny to validate local text-generation plumbing before trying larger models.",
        "- `llama-cpp-python` is a follow-up runtime candidate because native build/CUDA support must be proven separately.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe isolated LLM env candidates.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-env", default="llm_env")
    args = parser.parse_args()

    env = detect_environment(args.target_env)
    candidates = [evaluate_candidate(candidate, env) for candidate in CANDIDATES]
    try:
        result_rel = str(args.output.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        result_rel = str(args.output)
    payload = {
        "metadata": {
            "schema_version": "llm-env-candidate-probe-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "environment": env,
            "result_json": result_rel,
        },
        "result": {
            "task": "llm_isolated_env_candidate_probe",
            "existing_env_modified": False,
            "install_command_executed": False,
            "download_command_executed": False,
            "candidate_count": len(candidates),
            "candidates": candidates,
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
