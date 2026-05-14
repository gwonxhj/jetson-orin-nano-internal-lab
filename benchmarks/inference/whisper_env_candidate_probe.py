#!/usr/bin/env python3
"""Probe isolated Whisper environment candidates without installing them."""

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
    expected_device_path: str
    trust_level: str
    notes: str


CANDIDATES = [
    Candidate(
        name="openai_whisper_clone_yolo",
        backend="openai-whisper",
        package="openai-whisper",
        install_spec="openai-whisper",
        env_strategy="conda clone yolo_env, then pip install openai-whisper",
        runtime_engine="PyTorch",
        expected_device_path="cuda if cloned torch remains usable, cpu fallback otherwise",
        trust_level="upstream_open_source_package",
        notes="Best first candidate because yolo_env already has Jetson PyTorch CUDA; clone keeps the stable env untouched.",
    ),
    Candidate(
        name="faster_whisper_clone_yolo",
        backend="faster-whisper",
        package="faster-whisper",
        install_spec="faster-whisper",
        env_strategy="conda clone yolo_env, then pip install faster-whisper",
        runtime_engine="CTranslate2",
        expected_device_path="cpu likely first; cuda depends on CTranslate2 aarch64/CUDA wheel compatibility",
        trust_level="upstream_open_source_package",
        notes="Good follow-up for optimized inference, but Jetson CUDA wheel compatibility must be proven in isolation.",
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
        "platform": platform.platform(),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "target_env": target_env,
        "target_env_exists": conda_env_exists(target_env),
        "ffmpeg": run_command(["ffmpeg", "-version"]),
        "torch": detect_torch(),
        "current_packages": {
            "whisper": package_available("whisper"),
            "faster_whisper": package_available("faster_whisper"),
        },
    }


def evaluate_candidate(candidate: Candidate, env: dict[str, Any]) -> dict[str, Any]:
    python_matches = env["python_tag"] == "cp310"
    platform_matches = env["machine"] == "aarch64"
    ffmpeg_available = env["ffmpeg"].get("exit_code") == 0
    torch_cuda_available = bool(env["torch"].get("cuda_available"))
    current_env_clean = not env["current_packages"]["whisper"] and not env["current_packages"]["faster_whisper"]
    target_free = not env["target_env_exists"]
    if candidate.backend == "openai-whisper":
        verdict = "recommended_first_isolated_candidate" if python_matches and platform_matches and ffmpeg_available and torch_cuda_available and target_free else "requires_review"
    else:
        verdict = "secondary_isolated_candidate_requires_cuda_validation" if python_matches and platform_matches and ffmpeg_available and target_free else "requires_review"
    return {
        "name": candidate.name,
        "backend": candidate.backend,
        "package": candidate.package,
        "install_spec": candidate.install_spec,
        "env_strategy": candidate.env_strategy,
        "runtime_engine": candidate.runtime_engine,
        "expected_device_path": candidate.expected_device_path,
        "trust_level": candidate.trust_level,
        "notes": candidate.notes,
        "checks": {
            "python_cp310": python_matches,
            "platform_aarch64": platform_matches,
            "ffmpeg_available": ffmpeg_available,
            "torch_cuda_available_in_source_env": torch_cuda_available,
            "current_yolo_env_not_modified": current_env_clean,
            "target_env_free": target_free,
        },
        "candidate_verdict": verdict,
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    rows = [
        f"| {item['backend']} | `{item['install_spec']}` | {item['runtime_engine']} | `{item['candidate_verdict']}` |"
        for item in result["candidates"]
    ]
    env = meta["environment"]
    return "\n".join([
        "# Whisper Env Candidate Probe",
        "",
        "> 기존 `yolo_env`를 변경하지 않고 Whisper transcription 성공 evidence로 넘어가기 위한 격리 env 후보 검증입니다.",
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
        f"| ffmpeg available | {env['ffmpeg'].get('exit_code') == 0} |",
        f"| Torch CUDA available | {env['torch'].get('cuda_available', False)} |",
        f"| Current whisper packages | `whisper={env['current_packages']['whisper']}`, `faster_whisper={env['current_packages']['faster_whisper']}` |",
        f"| Result JSON | `{meta['result_json']}` |",
        "",
        "## Candidate Summary",
        "",
        "| Backend | Install spec | Runtime engine | Verdict |",
        "|---|---|---|---|",
        *rows,
        "",
        "## Recommended Flow",
        "",
        "1. Keep `yolo_env` unchanged.",
        "2. Run `bash scripts/create_whisper_env.sh` first and review the plan.",
        "3. Create the isolated env only with `bash scripts/create_whisper_env.sh --execute`.",
        "4. Activate or use `conda run -n whisper_env` and rerun `bash scripts/run_whisper_smoke.sh tiny` from the isolated env.",
        "5. Treat `openai-whisper` as the first candidate and `faster-whisper` as a follow-up optimization candidate.",
        "",
        "## Notes",
        "",
        "- This probe does not install packages, create envs, or download model weights.",
        "- `openai-whisper` is preferred first because it can reuse the cloned Jetson PyTorch CUDA stack.",
        "- `faster-whisper` may be faster, but CTranslate2 CUDA support on Jetson must be proven separately.",
        "- A successful transcription smoke is still audio inference path evidence, not deployment readiness or accuracy benchmarking.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe isolated Whisper env candidates.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--target-env", default="whisper_env")
    args = parser.parse_args()

    env = detect_environment(args.target_env)
    candidates = [evaluate_candidate(candidate, env) for candidate in CANDIDATES]
    try:
        result_rel = str(args.output.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        result_rel = str(args.output)
    payload = {
        "metadata": {
            "schema_version": "whisper-env-candidate-probe-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "environment": env,
            "result_json": result_rel,
        },
        "result": {
            "task": "whisper_isolated_env_candidate_probe",
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
