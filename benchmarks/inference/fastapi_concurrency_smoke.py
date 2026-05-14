#!/usr/bin/env python3
"""Measure localhost FastAPI ResNet18 concurrency smoke behavior."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import platform
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def timed_request(base_url: str, endpoint: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=timeout_s)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.raise_for_status()
        body = response.json()
        return {
            "ok": True,
            "client_ms": elapsed_ms,
            "server_ms": float(body["result"]["inference_ms"]),
            "output_shape": body["result"]["output_shape"],
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {"ok": False, "client_ms": elapsed_ms, "error": repr(exc)}


def parse_levels(text: str) -> list[int]:
    levels = [int(part.strip()) for part in text.split(",") if part.strip()]
    if not levels or any(level < 1 for level in levels):
        raise ValueError("concurrency levels must be positive integers")
    return levels


def run_level(base_url: str, endpoint: str, request_payload: dict[str, Any], concurrency: int, request_count: int, timeout_s: float) -> dict[str, Any]:
    total = max(request_count, concurrency)
    start = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(timed_request, base_url, endpoint, request_payload, timeout_s) for _ in range(total)]
        for future in as_completed(futures):
            results.append(future.result())
    wall_ms = (time.perf_counter() - start) * 1000.0
    successes = [item for item in results if item["ok"]]
    failures = [item for item in results if not item["ok"]]
    client_samples = [float(item["client_ms"]) for item in successes]
    server_samples = [float(item["server_ms"]) for item in successes]
    return {
        "concurrency": concurrency,
        "requests": total,
        "success_count": len(successes),
        "error_count": len(failures),
        "errors": [item.get("error", "unknown") for item in failures[:5]],
        "wall_ms": round(wall_ms, 4),
        "throughput_rps": round(len(successes) / (wall_ms / 1000.0), 4) if wall_ms else 0.0,
        "client_roundtrip_ms": summarize(client_samples),
        "server_inference_ms": summarize(server_samples),
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    lines = [
        "# FastAPI ResNet18 Concurrency Smoke Report",
        "",
        "> ResNet18 synthetic inference endpoint에 대해 localhost 동시 요청 smoke를 기록한 보고서입니다.",
        "> 이 결과는 짧은 concurrency path evidence이며 deployment-ready, load test, soak test evidence가 아닙니다.",
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
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Backend | {result['backend']} |",
        f"| Precision | {result['precision']} |",
        f"| Input shape | {result['input']['shape']} |",
        f"| Warmup | {result['runtime']['warmup']} |",
        f"| Requests per level | {result['runtime']['requests_per_level']} |",
        "",
        "## Concurrency Results",
        "",
        "| Concurrency | Requests | Success | Errors | Wall ms | Throughput rps | Client mean ms | Client p95 ms | Server mean ms | Server p95 ms |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for level in result["levels"]:
        client = level["client_roundtrip_ms"]
        server = level["server_inference_ms"]
        lines.append(
            f"| {level['concurrency']} | {level['requests']} | {level['success_count']} | {level['error_count']} | "
            f"{level['wall_ms']} | {level['throughput_rps']} | {client.get('mean_ms', 'n/a')} | "
            f"{client.get('p95_ms', 'n/a')} | {server.get('mean_ms', 'n/a')} | {server.get('p95_ms', 'n/a')} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This is localhost concurrency smoke, not deployment approval.",
        "- Throughput is measured from client-side wall time for each concurrency level.",
        "- Server inference timing is still measured inside the handler around the PyTorch model call.",
        "- Compare this evidence only as a serving-layer system comparison, not as a direct regression against TensorRT or ONNX Runtime.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FastAPI ResNet18 localhost concurrency smoke.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", default="")
    parser.add_argument("--tegrastats-log", default="")
    parser.add_argument("--levels", default="1,2,4")
    parser.add_argument("--requests-per-level", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    args = parser.parse_args()

    levels = parse_levels(args.levels)
    health = wait_for_health(args.base_url, timeout_s=60.0)
    models = requests.get(f"{args.base_url}/v1/models", timeout=5).json()
    endpoint = "/v1/infer/resnet18/synthetic"
    request_payload = {"batch_size": args.batch_size, "height": args.height, "width": args.width, "seed": args.seed}

    for _ in range(args.warmup):
        response = requests.post(f"{args.base_url}{endpoint}", json=request_payload, timeout=args.timeout)
        response.raise_for_status()

    level_results = [
        run_level(args.base_url, endpoint, request_payload, concurrency, args.requests_per_level, args.timeout)
        for concurrency in levels
    ]
    failures = [level for level in level_results if level["error_count"] > 0]
    if failures:
        raise RuntimeError(f"concurrency smoke had request errors: {failures}")

    model_info = models["models"][0]
    payload = {
        "metadata": {
            "schema_version": "fastapi-concurrency-smoke-v1",
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
            "task": "local_inference_api_concurrency_smoke",
            "server": {"framework": "fastapi", "asgi": "uvicorn", "base_url": args.base_url, "endpoint": endpoint, "health": health},
            "framework": "pytorch",
            "backend": model_info["device"],
            "precision": model_info["precision"],
            "model": model_info,
            "input": {"source": "synthetic_random_tensor", "shape": [args.batch_size, 3, args.height, args.width], "dtype": "float32", "seed": args.seed},
            "runtime": {
                "warmup": args.warmup,
                "concurrency_levels": levels,
                "requests_per_level": args.requests_per_level,
                "timing": "client_wall_time_by_concurrency_level_and_server_handler_inference",
            },
            "levels": level_results,
            "interpretation": {
                "deployment_ready_claim": False,
                "load_test_claim": False,
                "network_latency_claim": False,
                "external_sensor_dependency": False,
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
