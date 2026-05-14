#!/usr/bin/env python3
"""Whisper offline transcription smoke benchmark.

This runner does not install packages or download model weights by default.
Missing package/model states are written as valid evidence so the Jetson Python
environment can stay stable while the audio inference path is introduced.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MODEL_CACHE_FILES = {
    "tiny": "tiny.pt",
    "base": "base.pt",
}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        home = str(Path.home())
        text = str(path)
        if text.startswith(home):
            return text.replace(home, "[home]", 1)
        return text


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_command(command: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    except Exception as exc:
        return {"command": command, "error": repr(exc)}


def safe_git_status() -> dict[str, Any]:
    status = run_command(["git", "status", "--short", "--branch"])
    if "stdout" in status:
        status["stdout"] = "[captured during evidence generation; see committed git history for final state]"
    return status


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def generate_tone_wav(path: Path, sample_rate: int, duration_s: float, frequency_hz: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_count = int(sample_rate * duration_s)
    amplitude = 0.2
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_count):
            value = int(32767 * amplitude * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def wav_metadata(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        return {
            "path": display_path(path),
            "sha256": sha256_file(path),
            "format": "wav",
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "sample_rate_hz": sample_rate,
            "frames": frames,
            "duration_s": round(frames / sample_rate, 4) if sample_rate else 0.0,
        }


def default_cache_path(model_name: str) -> Path:
    return Path.home() / ".cache" / "whisper" / MODEL_CACHE_FILES[model_name]


def whisper_package_info() -> dict[str, Any]:
    spec = importlib.util.find_spec("whisper")
    if spec is None:
        return {"available": False, "module": "whisper", "version": ""}
    try:
        import whisper

        return {"available": True, "module": "whisper", "version": getattr(whisper, "__version__", "unknown")}
    except Exception as exc:
        return {"available": False, "module": "whisper", "version": "", "error": repr(exc)}


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    latency = result["latency_ms"]
    transcript = result["transcription"].get("text", "")
    transcript_preview = transcript if transcript else "(empty or not measured)"
    return "\n".join([
        "# Whisper Transcription Smoke Report",
        "",
        "> Whisper tiny/base offline transcription path를 Jetson에서 evidence로 남기기 위한 smoke report입니다.",
        "> Synthetic tone input은 accuracy evidence가 아니라 audio decode/model path evidence입니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['conda_env']}` |",
        f"| Python | `{meta['python_version']}` |",
        f"| Package | `{meta['package']['module']}` available: {meta['package']['available']} |",
        f"| Model | `{result['model']['name']}` |",
        f"| Status | `{result['status']}` |",
        f"| Failure reason | `{result['failure_reason'] or 'none'}` |",
        "",
        "## Audio Input",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Path | `{result['audio']['path']}` |",
        f"| SHA256 | `{result['audio']['sha256']}` |",
        f"| Duration s | {result['audio']['duration_s']} |",
        f"| Sample rate Hz | {result['audio']['sample_rate_hz']} |",
        f"| Source | `{result['audio']['source']}` |",
        "",
        "## Runtime",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Warmup | {result['runtime']['warmup']} |",
        f"| Repeat | {result['runtime']['repeat']} |",
        f"| Mean ms | {latency.get('mean_ms', 'not measured')} |",
        f"| P95 ms | {latency.get('p95_ms', 'not measured')} |",
        f"| Real-time factor | {result['runtime'].get('real_time_factor', 'not measured')} |",
        "",
        "## Transcript Preview",
        "",
        "```text",
        transcript_preview,
        "```",
        "",
        "## Interpretation",
        "",
        "- This runner does not install packages or download model weights by default.",
        "- `dependency_missing` and `model_missing` are valid evidence states, not test failures.",
        "- Synthetic tone input does not prove speech recognition quality.",
        "- A future speech sample should be committed only if it is safe to publish and license-clear.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Whisper tiny/base offline transcription smoke.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--audio", type=Path, default=Path("artifacts/audio/whisper_smoke_16khz.wav"))
    parser.add_argument("--model", choices=["tiny", "base"], default="tiny")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--language", default="en")
    parser.add_argument("--offline-only", action="store_true", default=True)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    if not args.audio.exists():
        generate_tone_wav(args.audio, sample_rate=16000, duration_s=1.0, frequency_hz=440.0)

    audio = wav_metadata(args.audio)
    audio["source"] = "generated_synthetic_tone_no_speech_accuracy_claim"
    package = whisper_package_info()
    cache_path = default_cache_path(args.model)
    cache_present = cache_path.exists()
    status = "dependency_missing"
    failure_reason = ""
    latency = {"samples_ms": [], "count": 0}
    transcription: dict[str, Any] = {"text": "", "segments": [], "language": args.language}
    runtime_extra: dict[str, Any] = {}

    if package["available"]:
        if args.offline_only and not args.allow_download and not cache_present:
            status = "model_missing"
            failure_reason = f"offline model cache not found: {display_path(cache_path)}"
        else:
            try:
                import whisper

                import torch

                if args.device == "auto":
                    device_name = "cuda" if torch.cuda.is_available() else "cpu"
                else:
                    device_name = args.device
                if device_name == "cuda" and not torch.cuda.is_available():
                    raise RuntimeError("requested CUDA but torch.cuda.is_available() is False")

                model = whisper.load_model(args.model, device=device_name, download_root=str(cache_path.parent))

                def work() -> dict[str, Any]:
                    return model.transcribe(str(args.audio), language=args.language, fp16=(device_name == "cuda"))

                latency, last = timed_repeats(work, args.repeat, args.warmup)
                text = str(last.get("text", "")).strip()
                transcription = {
                    "text": text,
                    "language": last.get("language", args.language),
                    "segments": [
                        {"start": round(float(segment.get("start", 0.0)), 3), "end": round(float(segment.get("end", 0.0)), 3), "text": str(segment.get("text", "")).strip()}
                        for segment in last.get("segments", [])
                    ],
                }
                status = "succeeded"
                if latency.get("mean_ms") and audio["duration_s"]:
                    runtime_extra["real_time_factor"] = round((latency["mean_ms"] / 1000.0) / audio["duration_s"], 4)
                runtime_extra["device"] = device_name
                runtime_extra["torch_version"] = torch.__version__
            except Exception as exc:
                status = "failed"
                failure_reason = repr(exc)

    payload = {
        "metadata": {
            "schema_version": "whisper-transcription-smoke-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": display_path(Path(sys.executable)),
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "tegrastats_note": args.tegrastats_log or "not captured by this script",
            "package": package,
            "isolation": {
                "existing_env_modified": False,
                "install_command_executed": False,
                "download_allowed": bool(args.allow_download),
                "offline_only": bool(args.offline_only and not args.allow_download),
            },
        },
        "result": {
            "task": "audio_transcription_smoke",
            "framework": "whisper",
            "backend": runtime_extra.get("device", args.device),
            "precision": "fp32_or_fp16_by_device",
            "status": status,
            "success": status == "succeeded",
            "failure_reason": failure_reason,
            "model": {
                "name": args.model,
                "family": "whisper",
                "cache_path": display_path(cache_path),
                "cache_present": cache_present,
            },
            "audio": audio,
            "runtime": {
                "warmup": args.warmup,
                "repeat": args.repeat,
                "language": args.language,
                **runtime_extra,
            },
            "latency_ms": latency,
            "transcription": transcription,
            "interpretation": {
                "accuracy_claim": False,
                "deployment_ready_claim": False,
                "external_sensor_dependency": False,
                "notes": "Synthetic tone input is used only to validate the local audio inference path.",
            },
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
