#!/usr/bin/env python3
"""Measure localhost FastAPI Whisper speech transcription smoke latency."""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests


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


def normalize_transcript(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


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


def wait_for_health(base_url: str, timeout_s: float) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                return response.json()
            last_error = f"status={response.status_code}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(0.25)
    raise RuntimeError(f"server did not become healthy within {timeout_s}s: {last_error}")


def timed_call(fn: Callable[[], requests.Response]) -> tuple[float, requests.Response]:
    start = time.perf_counter()
    response = fn()
    return (time.perf_counter() - start) * 1000.0, response


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    client = result["latency"]["client_roundtrip_ms"]
    server = result["latency"]["server_inference_ms"]

    def latency_value(summary: dict[str, Any], key: str) -> Any:
        return summary.get(key, "not measured")

    return "\n".join([
        "# FastAPI Whisper Speech Server Smoke Report",
        "",
        "> Whisper tiny CUDA transcription path를 localhost FastAPI serving layer로 감싼 smoke evidence입니다.",
        "> License-clear generated speech input을 사용하므로 broad accuracy evidence나 deployment-ready evidence가 아닙니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Base URL | `{result['server']['base_url']}` |",
        f"| Endpoint | `{result['server']['endpoint']}` |",
        f"| Server log | `{meta['server_log']}` |",
        f"| Tegrastats log | `{meta['tegrastats_log']}` |",
        "",
        "## Model / Audio",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | {result['model']['id']} |",
        f"| Backend | {result['backend']} |",
        f"| Precision | {result['precision']} |",
        f"| Audio path | `{result['input']['path']}` |",
        f"| Audio SHA256 | `{result['input']['sha256']}` |",
        f"| Expected text | `{result['transcription']['expected_text']}` |",
        f"| Transcript | `{result['transcription']['text']}` |",
        f"| Expected matched | {result['transcription']['normalized_contains_expected']} |",
        "",
        "## Latency",
        "",
        "| Metric | Mean ms | P95 ms | P99 ms |",
        "|---|---:|---:|---:|",
        f"| Client roundtrip | {latency_value(client, 'mean_ms')} | {latency_value(client, 'p95_ms')} | {latency_value(client, 'p99_ms')} |",
        f"| Server transcription | {latency_value(server, 'mean_ms')} | {latency_value(server, 'p95_ms')} | {latency_value(server, 'p99_ms')} |",
        "",
        "## Interpretation",
        "",
        "- Client roundtrip includes localhost HTTP serialization, FastAPI routing, audio path validation, transcription, and response serialization.",
        "- Server transcription is measured inside the FastAPI handler around `model.transcribe`.",
        "- This is localhost serving-layer evidence, not production deployment approval.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FastAPI Whisper localhost speech smoke client.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", default="")
    parser.add_argument("--tegrastats-log", default="")
    parser.add_argument("--audio-path", default="examples/audio/license_clear_whisper_smoke.wav")
    parser.add_argument("--expected-text", default="hello world")
    parser.add_argument("--language", default="en")
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--require-success", action="store_true")
    args = parser.parse_args()

    health = wait_for_health(args.base_url, timeout_s=90.0)
    models = requests.get(f"{args.base_url}/v1/models", timeout=5).json()
    endpoint = "/v1/infer/whisper/speech"
    request_payload = {"audio_path": args.audio_path, "language": args.language, "expected_text": args.expected_text}

    for _ in range(args.warmup):
        response = requests.post(f"{args.base_url}{endpoint}", json=request_payload, timeout=120)
        response.raise_for_status()

    client_samples: list[float] = []
    server_samples: list[float] = []
    last_payload: dict[str, Any] | None = None
    for _ in range(args.repeat):
        elapsed_ms, response = timed_call(lambda: requests.post(f"{args.base_url}{endpoint}", json=request_payload, timeout=120))
        response.raise_for_status()
        last_payload = response.json()
        client_samples.append(elapsed_ms)
        if last_payload["result"]["inference_ms"] is not None:
            server_samples.append(float(last_payload["result"]["inference_ms"]))

    assert last_payload is not None
    if args.require_success and not last_payload.get("success"):
        raise RuntimeError(f"Whisper serving smoke did not succeed: {last_payload.get('failure_reason')}")

    normalized_text = normalize_transcript(last_payload["result"].get("text", ""))
    normalized_expected = normalize_transcript(args.expected_text)
    model_info = next((item for item in models["models"] if item["id"].startswith("whisper-")), last_payload["model"])
    payload = {
        "metadata": {
            "schema_version": "fastapi-whisper-server-smoke-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "server_log": args.server_log or "not captured",
            "tegrastats_log": args.tegrastats_log or "not captured",
        },
        "result": {
            "task": "local_audio_transcription_api_smoke",
            "server": {"framework": "fastapi", "asgi": "uvicorn", "base_url": args.base_url, "endpoint": endpoint, "health": health},
            "framework": "whisper",
            "backend": last_payload["backend"],
            "precision": last_payload["precision"],
            "status": last_payload["status"],
            "success": last_payload["success"],
            "failure_reason": last_payload.get("failure_reason", ""),
            "model": model_info,
            "input": last_payload["input"],
            "runtime": {"warmup": args.warmup, "repeat": args.repeat, "timing": "client_roundtrip_and_server_handler_transcription"},
            "latency": {
                "client_roundtrip_ms": summarize(client_samples),
                "server_inference_ms": summarize(server_samples),
            },
            "transcription": {
                "text": last_payload["result"].get("text", ""),
                "expected_text": args.expected_text,
                "normalized_text": normalized_text,
                "normalized_expected_text": normalized_expected,
                "normalized_contains_expected": bool(normalized_expected and normalized_expected in normalized_text),
                "language": last_payload["result"].get("language", args.language),
                "segments": last_payload["result"].get("segments", []),
            },
            "interpretation": last_payload.get("interpretation", {}),
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
