#!/usr/bin/env python3
"""Probe Jetson ONNX Runtime GPU wheel candidates without installing them.

This records compatibility evidence for JetPack 6 / CUDA 12.6 / cuDNN 9
without mutating the current Python environment. Network failures are captured
as evidence instead of treated as test failures.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Candidate:
    name: str
    version: str
    source: str
    url: str
    package: str
    python_tag: str
    platform_tag: str
    trust_level: str
    install_hint: str
    notes: str


CANDIDATES = [
    Candidate(
        name="jetson_ai_lab_index_jp6_cu126",
        version="1.23.0",
        source="pypi.jetson-ai-lab.io jp6/cu126 index",
        url="https://pypi.jetson-ai-lab.io/jp6/cu126",
        package="onnxruntime-gpu",
        python_tag="cp310",
        platform_tag="linux_aarch64",
        trust_level="nvidia_forum_recommended_index",
        install_hint="python3 -m pip install --extra-index-url https://pypi.jetson-ai-lab.io/jp6/cu126 onnxruntime-gpu==1.23.0",
        notes="Preferred candidate for JetPack 6 / CUDA 12.6 if reachable from the Jetson.",
    ),
    Candidate(
        name="jetson_ai_lab_direct_wheel_1_20_2",
        version="1.20.2",
        source="pypi.jetson-ai-lab.io direct wheel",
        url="https://pypi.jetson-ai-lab.io/jp6/cu126/+f/f6e/2baa664069470/onnxruntime_gpu-1.20.2-cp310-cp310-linux_aarch64.whl#sha256=f6e2baa664069470c6574219a79aba315e26c76db49d347678a5a273f1c41c9a",
        package="onnxruntime-gpu",
        python_tag="cp310",
        platform_tag="linux_aarch64",
        trust_level="nvidia_forum_confirmed_direct_wheel",
        install_hint="python3 -m pip install 'https://pypi.jetson-ai-lab.io/jp6/cu126/+f/f6e/2baa664069470/onnxruntime_gpu-1.20.2-cp310-cp310-linux_aarch64.whl#sha256=f6e2baa664069470c6574219a79aba315e26c76db49d347678a5a273f1c41c9a'",
        notes="Forum-confirmed to expose TensorrtExecutionProvider, CUDAExecutionProvider, and CPUExecutionProvider on JetPack 6.2.",
    ),
    Candidate(
        name="ultralytics_assets_direct_wheel_1_23_0",
        version="1.23.0",
        source="Ultralytics GitHub assets mirror",
        url="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl",
        package="onnxruntime-gpu",
        python_tag="cp310",
        platform_tag="linux_aarch64",
        trust_level="third_party_documented_mirror",
        install_hint="python3 -m pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl",
        notes="Documented by Ultralytics for JetPack 6 Python 3.10; use only if the Jetson AI Lab index is unavailable.",
    ),
    Candidate(
        name="ultralytics_assets_direct_wheel_1_20_0",
        version="1.20.0",
        source="Ultralytics GitHub assets mirror",
        url="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl",
        package="onnxruntime-gpu",
        python_tag="cp310",
        platform_tag="linux_aarch64",
        trust_level="third_party_documented_mirror",
        install_hint="python3 -m pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl",
        notes="Fallback mirror candidate; lower priority than Jetson AI Lab index/direct wheel.",
    ),
]

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


def detect_cudnn() -> dict[str, Any]:
    candidates = [
        Path("/usr/include/aarch64-linux-gnu/cudnn_version.h"),
        Path("/usr/include/cudnn_version.h"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        values: dict[str, str] = {}
        for key in ("CUDNN_MAJOR", "CUDNN_MINOR", "CUDNN_PATCHLEVEL"):
            match = re.search(rf"#define\s+{key}\s+(\d+)", text)
            if match:
                values[key] = match.group(1)
        if values:
            version = ".".join([values.get("CUDNN_MAJOR", ""), values.get("CUDNN_MINOR", ""), values.get("CUDNN_PATCHLEVEL", "")]).strip(".")
            return {"path": str(path), "version": version, "major": values.get("CUDNN_MAJOR", "")}
    return {"path": "", "version": "", "major": ""}


def detect_cuda() -> dict[str, Any]:
    version_json = Path("/usr/local/cuda/version.json")
    if version_json.exists():
        try:
            payload = json.loads(version_json.read_text(encoding="utf-8"))
            version = payload.get("cuda", {}).get("version", "")
            return {"source": str(version_json), "version": version, "major_minor": ".".join(version.split(".")[:2]), "raw": payload.get("cuda", {})}
        except Exception as exc:
            return {"source": str(version_json), "error": repr(exc)}
    nvcc = run_command(["/usr/local/cuda/bin/nvcc", "--version"])
    stdout = nvcc.get("stdout", "")
    match = re.search(r"release\s+(\d+\.\d+)", stdout)
    if match:
        return {"source": "/usr/local/cuda/bin/nvcc", "version": match.group(1), "major_minor": match.group(1), "raw": nvcc}
    nvcc_path = run_command(["nvcc", "--version"])
    stdout = nvcc_path.get("stdout", "")
    match = re.search(r"release\s+(\d+\.\d+)", stdout)
    if match:
        return {"source": "PATH:nvcc", "version": match.group(1), "major_minor": match.group(1), "raw": nvcc_path}
    return {"source": "", "version": "", "major_minor": "", "raw": nvcc_path}


def detect_environment() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_executable": "python3 (yolo_env)" if os.environ.get("CONDA_DEFAULT_ENV") == "yolo_env" else Path(sys.executable).name,
        "python_tag": f"cp{sys.version_info.major}{sys.version_info.minor}",
        "machine": platform.machine(),
        "platform": platform.platform(),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "l4t": run_command(["cat", "/etc/nv_tegra_release"]),
        "cuda": detect_cuda(),
        "cudnn": detect_cudnn(),
        "onnxruntime_current": run_command([sys.executable, "-c", "import onnxruntime as ort; print(ort.__version__); print(ort.get_available_providers())"]),
    }


def check_url(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "jetson-orin-nano-internal-lab/ort-cuda-probe"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(65536)
            return {
                "reachable": True,
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "content_length": response.headers.get("content-length", ""),
                "sample_contains_onnxruntime_gpu": b"onnxruntime" in body.lower(),
            }
    except urllib.error.HTTPError as exc:
        return {"reachable": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"reachable": False, "error": repr(exc)}


def evaluate_candidate(candidate: Candidate, env: dict[str, Any], skip_network: bool, timeout: int) -> dict[str, Any]:
    python_matches = candidate.python_tag == env["python_tag"]
    platform_matches = env["machine"] == "aarch64" and candidate.platform_tag == "linux_aarch64"
    cuda_matches = env["cuda"].get("major_minor") == "12.6"
    cudnn_major_matches = env["cudnn"].get("major") == "9"
    network = {"checked": False}
    if not skip_network:
        network = {"checked": True, **check_url(candidate.url, timeout)}
    compatible = python_matches and platform_matches and cuda_matches and cudnn_major_matches
    return {
        "name": candidate.name,
        "version": candidate.version,
        "source": candidate.source,
        "url": candidate.url,
        "package": candidate.package,
        "python_tag": candidate.python_tag,
        "platform_tag": candidate.platform_tag,
        "trust_level": candidate.trust_level,
        "install_hint": candidate.install_hint,
        "notes": candidate.notes,
        "checks": {
            "python_tag_matches": python_matches,
            "platform_matches": platform_matches,
            "cuda_12_6_detected": cuda_matches,
            "cudnn_9_detected": cudnn_major_matches,
            "network": network,
        },
        "candidate_verdict": "compatible_candidate" if compatible else "incompatible_with_current_environment",
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    rows = []
    for item in result["candidates"]:
        network = item["checks"]["network"]
        reachable = network.get("reachable", "not checked")
        rows.append(f"| {item['name']} | {item['version']} | {item['trust_level']} | {item['candidate_verdict']} | {reachable} |")
    return "\n".join([
        "# ONNX Runtime CUDA Env Candidate Probe", "",
        "> 기존 `yolo_env`를 변경하지 않고 JetPack 6 / CUDA 12.6 / cuDNN 9 조합에서 사용할 수 있는 ONNX Runtime GPU wheel 후보를 검증한 evidence입니다.", "",
        "## Environment", "", "| Field | Value |", "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['environment']['conda_env']}` |",
        f"| Python tag | `{meta['environment']['python_tag']}` |",
        f"| Machine | `{meta['environment']['machine']}` |",
        f"| CUDA | `{meta['environment']['cuda'].get('version', '')}` |",
        f"| cuDNN | `{meta['environment']['cudnn'].get('version', '')}` |",
        f"| Result JSON | `{meta['result_json']}` |", "",
        "## Candidate Summary", "", "| Candidate | Version | Trust level | Verdict | URL reachable |", "|---|---:|---|---|---|",
        *rows, "",
        "## Recommended Flow", "",
        "1. Keep `yolo_env` unchanged.",
        "2. Use `scripts/create_ort_cuda_env.sh --execute` only when ready to create an isolated env.",
        "3. Prefer the Jetson AI Lab `jp6/cu126` index or NVIDIA-forum-confirmed direct wheel before third-party mirrors.",
        "4. After install, run `benchmarks/inference/onnxruntime_cuda_ep_attempt.py` from the isolated env and record provider availability again.", "",
        "## Notes", "",
        "- Candidate compatibility means the wheel tags and detected Jetson runtime family match; it is not a deployment-ready claim.",
        "- Network reachability is recorded separately because package hosts can be temporarily unavailable.",
        "- If CUDAExecutionProvider appears, add ONNX Runtime CUDA as a new runtime row instead of replacing existing CPU evidence.", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe ONNX Runtime GPU wheel candidates for Jetson.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    env = detect_environment()
    candidates = [evaluate_candidate(candidate, env, args.skip_network, args.timeout) for candidate in CANDIDATES]
    try:
        result_rel = str(args.output.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        result_rel = str(args.output)

    payload = {
        "metadata": {
            "schema_version": "ort-cuda-wheel-candidate-probe-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "environment": env,
            "result_json": result_rel,
        },
        "result": {
            "task": "onnxruntime_gpu_wheel_candidate_probe",
            "existing_env_modified": False,
            "install_command_executed": False,
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
