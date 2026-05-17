#!/usr/bin/env python3
"""Run a sustained multi-workload runtime interaction scenario.

The scenario combines:
- YOLO file-image detection loop
- FastAPI ResNet18 synthetic concurrent requests
- FastAPI Whisper speech transcription burst

This is runtime behavior evidence, not a production stress test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import queue
import statistics
import subprocess
import threading
from collections import defaultdict
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
RESNET_ENDPOINT = "/v1/infer/resnet18/synthetic"
WHISPER_ENDPOINT = "/v1/infer/whisper/speech"
DEFAULT_YOLO_MODEL = "yolov8n.pt"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(samples_ms: list[float]) -> dict[str, Any]:
    ordered = sorted(samples_ms)
    if not ordered:
        return {"count": 0, "samples_ms": []}

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
        "count": len(samples_ms),
        "mean_ms": round(statistics.fmean(samples_ms), 4),
        "min_ms": round(min(samples_ms), 4),
        "p50_ms": round(percentile(0.50), 4),
        "p95_ms": round(percentile(0.95), 4),
        "p99_ms": round(percentile(0.99), 4),
        "max_ms": round(max(samples_ms), 4),
        "samples_ms": [round(value, 4) for value in samples_ms],
    }


def bounded_sleep(seconds: float, stop_at: float) -> None:
    remaining = min(seconds, max(0.0, stop_at - time.perf_counter()))
    if remaining > 0:
        time.sleep(remaining)


def package_asset_image() -> tuple[Path, str]:
    import ultralytics

    asset = Path(ultralytics.__file__).resolve().parent / "assets" / "bus.jpg"
    if not asset.exists():
        raise FileNotFoundError(f"ultralytics sample image not found: {asset}")
    return asset, "[site-packages]/ultralytics/assets/bus.jpg"


def resolve_yolo_model(model_name: str, allow_download: bool) -> Path:
    model_dir = ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / model_name
    if model_path.exists():
        return model_path
    if not allow_download:
        raise FileNotFoundError(f"{model_path} not found. Set YOLO_ALLOW_DOWNLOAD=1 to allow download.")
    from ultralytics import YOLO

    previous_cwd = Path.cwd()
    try:
        os.chdir(model_dir)
        YOLO(model_name)
    finally:
        os.chdir(previous_cwd)
    if not model_path.exists():
        raise FileNotFoundError(f"expected downloaded model at {model_path}")
    return model_path


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


def get_json(url: str, timeout_s: float) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout_s)
    response.raise_for_status()
    return response.json()


class TimelineRecorder:
    def __init__(self, scenario_started_at: float) -> None:
        self.scenario_started_at = scenario_started_at
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._active_by_workload: dict[str, int] = defaultdict(int)
        self._max_active_by_workload: dict[str, int] = defaultdict(int)
        self._completed_by_workload: dict[str, int] = defaultdict(int)
        self._failed_by_workload: dict[str, int] = defaultdict(int)

    def begin_request(self, workload: str) -> dict[str, Any]:
        with self._lock:
            self._active_by_workload[workload] += 1
            self._max_active_by_workload[workload] = max(self._max_active_by_workload[workload], self._active_by_workload[workload])
            return {
                "client_backlog_proxy_kind": "thread_inflight_request_count",
                "client_outstanding_at_start": self._active_by_workload[workload],
                "client_outstanding_max_seen": self._max_active_by_workload[workload],
            }

    def end_request(self, workload: str, ok: bool) -> dict[str, Any]:
        with self._lock:
            self._active_by_workload[workload] = max(0, self._active_by_workload[workload] - 1)
            self._completed_by_workload[workload] += 1
            if not ok:
                self._failed_by_workload[workload] += 1
            return {
                "client_outstanding_after_end": self._active_by_workload[workload],
                "client_completed_count": self._completed_by_workload[workload],
                "client_failed_count": self._failed_by_workload[workload],
            }

    def record(self, workload: str, operation: str, started_at: float, ended_at: float, ok: bool, details: dict[str, Any] | None = None, error: str = "") -> None:
        event = {
            "workload": workload,
            "operation": operation,
            "started_at_s": round(started_at - self.scenario_started_at, 4),
            "ended_at_s": round(ended_at - self.scenario_started_at, 4),
            "duration_ms": round((ended_at - started_at) * 1000.0, 4),
            "ok": ok,
            "error": error,
            "details": details or {},
        }
        with self._lock:
            self._events.append(event)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(self._events, key=lambda item: (item["started_at_s"], item["workload"]))

    def observability_snapshot(self) -> dict[str, Any]:
        with self._lock:
            workloads = {}
            all_workloads = sorted(set(self._active_by_workload) | set(self._max_active_by_workload) | set(self._completed_by_workload) | set(self._failed_by_workload))
            for workload in all_workloads:
                workloads[workload] = {
                    "active_at_end": int(self._active_by_workload[workload]),
                    "max_outstanding": int(self._max_active_by_workload[workload]),
                    "completed_count": int(self._completed_by_workload[workload]),
                    "failed_count": int(self._failed_by_workload[workload]),
                }
            return {
                "kind": "client_thread_outstanding_request_count",
                "queue_depth_available": False,
                "workloads": workloads,
                "totals": {
                    "active_at_end": sum(int(v) for v in self._active_by_workload.values()),
                    "max_outstanding_sum_by_workload": sum(int(v) for v in self._max_active_by_workload.values()),
                    "completed_count": sum(int(v) for v in self._completed_by_workload.values()),
                    "failed_count": sum(int(v) for v in self._failed_by_workload.values()),
                },
                "notes": "Client-side worker outstanding counts are a backlog proxy for this localhost evidence run; they are not an ASGI queue-depth measurement.",
            }


def run_fastapi_request(base_url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    response = requests.post(f"{base_url}{RESNET_ENDPOINT}", json=payload, timeout=timeout_s)
    response.raise_for_status()
    body = response.json()
    return {"server_ms": float(body["result"]["inference_ms"]), "output_shape": body["result"]["output_shape"]}


def run_whisper_request(base_url: str, audio_path: str, expected_text: str, language: str, timeout_s: float) -> dict[str, Any]:
    payload = {"audio_path": audio_path, "expected_text": expected_text, "language": language}
    response = requests.post(f"{base_url}{WHISPER_ENDPOINT}", json=payload, timeout=timeout_s)
    response.raise_for_status()
    body = response.json()
    return {
        "success": bool(body.get("success")),
        "status": body.get("status", "unknown"),
        "server_ms": body.get("result", {}).get("inference_ms"),
        "text": body.get("result", {}).get("text", ""),
        "failure_reason": body.get("failure_reason", ""),
    }


def fastapi_worker(worker_id: int, args: argparse.Namespace, recorder: TimelineRecorder, stop_at: float, payload: dict[str, Any]) -> None:
    while time.perf_counter() < stop_at:
        start = time.perf_counter()
        obs_start = recorder.begin_request("fastapi_resnet18")
        try:
            if args.mock_workloads:
                time.sleep(args.mock_fastapi_ms / 1000.0)
                details = {"worker_id": worker_id, "server_ms": args.mock_fastapi_ms, "mode": "mock"}
            else:
                details = run_fastapi_request(args.base_url, payload, args.timeout)
                details["worker_id"] = worker_id
            ok = True
            error = ""
        except Exception as exc:
            details = {"worker_id": worker_id}
            ok = False
            error = repr(exc)
        end = time.perf_counter()
        details.update(obs_start)
        details.update(recorder.end_request("fastapi_resnet18", ok))
        recorder.record("fastapi_resnet18", "concurrent_request", start, end, ok, details, error)
        bounded_sleep(args.fastapi_interval_sec, stop_at)


def whisper_burst(args: argparse.Namespace, recorder: TimelineRecorder, scenario_started_at: float, stop_at: float) -> None:
    target = scenario_started_at + args.whisper_start_sec
    while time.perf_counter() < min(target, stop_at):
        time.sleep(0.05)
    for index in range(args.whisper_repeat):
        if time.perf_counter() >= stop_at:
            return
        start = time.perf_counter()
        obs_start = recorder.begin_request("fastapi_whisper")
        try:
            if args.mock_workloads:
                time.sleep(args.mock_whisper_ms / 1000.0)
                details = {"burst_index": index, "status": "succeeded", "success": True, "mode": "mock"}
            else:
                details = run_whisper_request(args.base_url, args.audio_path, args.expected_text, args.language, args.timeout)
                details["burst_index"] = index
            ok = bool(details.get("success", True))
            error = "" if ok else str(details.get("failure_reason", "whisper request did not succeed"))
        except Exception as exc:
            details = {"burst_index": index}
            ok = False
            error = repr(exc)
        end = time.perf_counter()
        details.update(obs_start)
        details.update(recorder.end_request("fastapi_whisper", ok))
        recorder.record("fastapi_whisper", "transcription_burst", start, end, ok, details, error)
        bounded_sleep(args.whisper_interval_sec, stop_at)


def yolo_loop(args: argparse.Namespace, recorder: TimelineRecorder, stop_at: float, setup_queue: queue.Queue[dict[str, Any]]) -> None:
    if args.mock_workloads:
        setup_queue.put({"status": "mock", "model": args.yolo_model, "device": args.yolo_device})
        while time.perf_counter() < stop_at:
            start = time.perf_counter()
            time.sleep(args.mock_yolo_ms / 1000.0)
            end = time.perf_counter()
            recorder.record("yolo_detection", "file_image_detection", start, end, True, {"detection_count": 1, "mode": "mock"})
            bounded_sleep(args.yolo_interval_sec, stop_at)
        return

    try:
        import torch
        import ultralytics
        from ultralytics import YOLO

        if args.yolo_device == "auto":
            device_name = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device_name = args.yolo_device
        if device_name == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("requested CUDA YOLO device but torch.cuda.is_available() is False")
        model_path = resolve_yolo_model(args.yolo_model, os.environ.get("YOLO_ALLOW_DOWNLOAD", "0") == "1")
        if args.yolo_image:
            image_path = Path(args.yolo_image).resolve()
            image_display = str(args.yolo_image)
        else:
            image_path, image_display = package_asset_image()
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        model = YOLO(str(model_path))
        setup_queue.put({
            "status": "ready",
            "framework": "ultralytics",
            "package_version": ultralytics.__version__,
            "model": args.yolo_model,
            "model_path": str(model_path.relative_to(ROOT)),
            "model_sha256": sha256_file(model_path),
            "image_path": image_display,
            "image_sha256": sha256_file(image_path),
            "device": device_name,
            "precision": "fp32",
        })
    except Exception as exc:
        setup_queue.put({"status": "unavailable", "error": repr(exc), "model": args.yolo_model, "device": args.yolo_device})
        start = time.perf_counter()
        recorder.record("yolo_detection", "setup", start, start, False, {}, repr(exc))
        return

    while time.perf_counter() < stop_at:
        start = time.perf_counter()
        try:
            prediction = model.predict(source=str(image_path), device=device_name, imgsz=args.yolo_imgsz, conf=args.yolo_conf, verbose=False)
            if device_name == "cuda":
                torch.cuda.synchronize()
            first = prediction[0]
            detection_count = len(first.boxes) if first.boxes is not None else 0
            details = {"detection_count": detection_count, "device": device_name}
            ok = True
            error = ""
        except Exception as exc:
            details = {"device": device_name}
            ok = False
            error = repr(exc)
        end = time.perf_counter()
        recorder.record("yolo_detection", "file_image_detection", start, end, ok, details, error)
        bounded_sleep(args.yolo_interval_sec, stop_at)


def summarize_by_workload(events: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for workload in sorted({event["workload"] for event in events}):
        rows = [event for event in events if event["workload"] == workload]
        successes = [event for event in rows if event["ok"]]
        errors = [event for event in rows if not event["ok"]]
        summary[workload] = {
            "event_count": len(rows),
            "success_count": len(successes),
            "error_count": len(errors),
            "errors": [event["error"] for event in errors[:10] if event.get("error")],
            "latency_ms": summarize([float(event["duration_ms"]) for event in successes]),
        }
    return summary


def interaction_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    whisper_events = [event for event in events if event["workload"] == "fastapi_whisper"]
    yolo_events = [event for event in events if event["workload"] == "yolo_detection" and event["operation"] == "file_image_detection"]
    fastapi_events = [event for event in events if event["workload"] == "fastapi_resnet18"]
    if not whisper_events:
        return {"whisper_window_present": False, "notes": "No Whisper burst window was recorded."}

    window_start = min(float(event["started_at_s"]) for event in whisper_events)
    window_end = max(float(event["ended_at_s"]) for event in whisper_events)

    def bucket(rows: list[dict[str, Any]]) -> dict[str, Any]:
        before = [event for event in rows if float(event["ended_at_s"]) < window_start]
        during = [event for event in rows if float(event["started_at_s"]) <= window_end and float(event["ended_at_s"]) >= window_start]
        after = [event for event in rows if float(event["started_at_s"]) > window_end]
        return {
            "before_whisper_ms": summarize([float(event["duration_ms"]) for event in before if event["ok"]]),
            "during_whisper_ms": summarize([float(event["duration_ms"]) for event in during if event["ok"]]),
            "after_whisper_ms": summarize([float(event["duration_ms"]) for event in after if event["ok"]]),
        }

    return {
        "whisper_window_present": True,
        "whisper_window_s": {"start": round(window_start, 4), "end": round(window_end, 4)},
        "yolo_latency_by_window": bucket(yolo_events),
        "fastapi_resnet18_latency_by_window": bucket(fastapi_events),
        "interpretation": "Windowed latency buckets are interaction evidence only; they are not direct regression or production capacity proof.",
    }


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    lines = [
        "# Multi-Workload Sustained Runtime Report",
        "",
        "> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.",
        "> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Base URL | `{result['server']['base_url']}` |",
        f"| Duration | {result['scenario']['duration_s']} s |",
        f"| Server log | `{meta['server_log']}` |",
        f"| Tegrastats log | `{meta['tegrastats_log']}` |",
        f"| Mock workloads | {result['scenario']['mock_workloads']} |",
        "",
        "## Workload Summary",
        "",
        "| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for workload, item in result["summary_by_workload"].items():
        latency = item["latency_ms"]
        lines.append(
            f"| {workload} | {item['event_count']} | {item['success_count']} | {item['error_count']} | "
            f"{latency.get('mean_ms', 'n/a')} | {latency.get('p95_ms', 'n/a')} | {latency.get('max_ms', 'n/a')} |"
        )
    lines.extend(["", "## Interaction Window", ""])
    interaction = result["interaction"]
    if interaction.get("whisper_window_present"):
        window = interaction["whisper_window_s"]
        lines.append(f"- Whisper burst window: {window['start']}s -> {window['end']}s")
        for label, bucket in [("YOLO", interaction["yolo_latency_by_window"]), ("FastAPI ResNet18", interaction["fastapi_resnet18_latency_by_window"])]:
            lines.extend(["", f"### {label}", "", "| Window | Count | Mean ms | P95 ms | Max ms |", "|---|---:|---:|---:|---:|"])
            for key, title in [("before_whisper_ms", "Before Whisper"), ("during_whisper_ms", "During Whisper"), ("after_whisper_ms", "After Whisper")]:
                row = bucket[key]
                lines.append(f"| {title} | {row.get('count', 0)} | {row.get('mean_ms', 'n/a')} | {row.get('p95_ms', 'n/a')} | {row.get('max_ms', 'n/a')} |")
    else:
        lines.append("- Whisper burst window was not recorded.")
    serving = result.get("serving_observability", {})
    client = serving.get("client_backlog_proxy", {})
    server_after = serving.get("server_metrics_after", {})
    lines.extend([
        "",
        "## Serving Observability",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Client completed requests | {client.get('totals', {}).get('completed_count', 'n/a')} |",
        f"| Client failed requests | {client.get('totals', {}).get('failed_count', 'n/a')} |",
        f"| Client max outstanding sum | {client.get('totals', {}).get('max_outstanding_sum_by_workload', 'n/a')} |",
        f"| Server max in-flight requests | {server_after.get('max_inflight_requests', 'n/a')} |",
        f"| Server failed requests | {server_after.get('failed_requests', 'n/a')} |",
        f"| Dropped request count proxy | {serving.get('dropped_request_count_proxy', 'n/a')} |",
        "",
        "These counters are queue/backlog proxies for localhost evidence; they are not production queue-depth telemetry.",
    ])
    lines.extend([
        "",
        "## Boundary",
        "",
        "- This is multi-workload runtime interaction evidence, not a production stress test.",
        "- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.",
        "- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.",
        "- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sustained multi-workload runtime interaction evidence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:18085")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", default="")
    parser.add_argument("--tegrastats-log", default="")
    parser.add_argument("--duration-sec", type=float, default=180.0)
    parser.add_argument("--fastapi-concurrency", type=int, default=2)
    parser.add_argument("--fastapi-interval-sec", type=float, default=0.05)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--width", type=int, default=224)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--whisper-start-sec", type=float, default=30.0)
    parser.add_argument("--whisper-repeat", type=int, default=2)
    parser.add_argument("--whisper-interval-sec", type=float, default=2.0)
    parser.add_argument("--audio-path", default="examples/audio/license_clear_whisper_smoke.wav")
    parser.add_argument("--expected-text", default="hello world")
    parser.add_argument("--language", default="en")
    parser.add_argument("--yolo-model", default=DEFAULT_YOLO_MODEL)
    parser.add_argument("--yolo-image", default="")
    parser.add_argument("--yolo-device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--yolo-imgsz", type=int, default=640)
    parser.add_argument("--yolo-conf", type=float, default=0.25)
    parser.add_argument("--yolo-interval-sec", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--mock-workloads", action="store_true")
    parser.add_argument("--mock-yolo-ms", type=float, default=8.0)
    parser.add_argument("--mock-fastapi-ms", type=float, default=5.0)
    parser.add_argument("--mock-whisper-ms", type=float, default=20.0)
    args = parser.parse_args()

    if args.duration_sec <= 0:
        raise ValueError("--duration-sec must be > 0")
    if args.fastapi_concurrency < 1:
        raise ValueError("--fastapi-concurrency must be >= 1")
    if args.whisper_repeat < 0:
        raise ValueError("--whisper-repeat must be >= 0")
    if args.yolo_interval_sec < 0:
        raise ValueError("--yolo-interval-sec must be >= 0")

    if args.mock_workloads:
        health = {"status": "ok", "mode": "mock"}
        models = {"models": [{"id": "resnet18-mock", "device": "mock", "precision": "fp32"}]}
        metrics_before = {"status": "mock", "requests": {"total": 0}}
    else:
        health = wait_for_health(args.base_url, timeout_s=90.0)
        models = get_json(f"{args.base_url}/v1/models", timeout_s=5.0)
        metrics_before = get_json(f"{args.base_url}/metrics", timeout_s=5.0)

    scenario_started_at = time.perf_counter()
    stop_at = scenario_started_at + args.duration_sec
    recorder = TimelineRecorder(scenario_started_at)
    yolo_setup: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)

    request_payload = {"batch_size": args.batch_size, "height": args.height, "width": args.width, "seed": args.seed}
    threads: list[threading.Thread] = []
    threads.append(threading.Thread(target=yolo_loop, args=(args, recorder, stop_at, yolo_setup), name="yolo-loop"))
    threads.append(threading.Thread(target=whisper_burst, args=(args, recorder, scenario_started_at, stop_at), name="whisper-burst"))
    for worker_id in range(args.fastapi_concurrency):
        threads.append(threading.Thread(target=fastapi_worker, args=(worker_id, args, recorder, stop_at, request_payload), name=f"fastapi-{worker_id}"))

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=max(args.duration_sec + args.timeout + 10.0, 30.0))
        if thread.is_alive():
            raise RuntimeError(f"worker did not finish: {thread.name}")

    scenario_ended_at = time.perf_counter()
    events = recorder.snapshot()
    try:
        yolo_metadata = yolo_setup.get_nowait()
    except queue.Empty:
        yolo_metadata = {"status": "not_reported"}

    if args.mock_workloads:
        metrics_after = {"status": "mock", "requests": {"total": len(events)}}
    else:
        try:
            metrics_after = get_json(f"{args.base_url}/metrics", timeout_s=5.0)
        except Exception as exc:
            metrics_after = {"status": "unavailable", "error": repr(exc)}

    summary = summarize_by_workload(events)
    error_count = sum(item["error_count"] for item in summary.values())
    client_observability = recorder.observability_snapshot()
    server_observability_before = metrics_before.get("serving_observability", {}) if isinstance(metrics_before, dict) else {}
    server_observability_after = metrics_after.get("serving_observability", {}) if isinstance(metrics_after, dict) else {}
    serving_observability = {
        "server_metrics_before": server_observability_before,
        "server_metrics_after": server_observability_after,
        "client_backlog_proxy": client_observability,
        "failed_request_count": int(client_observability.get("totals", {}).get("failed_count", 0)) + int(server_observability_after.get("failed_requests", 0) or 0),
        "dropped_request_count_proxy": int(client_observability.get("totals", {}).get("failed_count", 0)) + int(server_observability_after.get("backlog_proxy", {}).get("dropped_request_count", 0) or 0),
        "notes": "Serving observability is bounded to localhost evidence: in-process server counters and client worker outstanding counts are retained as queue/backlog proxies.",
    }
    payload = {
        "metadata": {
            "schema_version": "multi-workload-sustained-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": "[conda-env]/bin/python3" if not args.mock_workloads else "mock",
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "server_log": args.server_log or "not captured",
            "tegrastats_log": args.tegrastats_log or "not captured",
        },
        "result": {
            "task": "multi_workload_sustained_runtime_interaction",
            "status": "completed_with_runtime_events" if error_count else "succeeded",
            "success": True,
            "error_count": error_count,
            "server": {"framework": "fastapi", "base_url": args.base_url, "health": health, "models": models},
            "scenario": {
                "duration_s": round(scenario_ended_at - scenario_started_at, 4),
                "target_duration_s": args.duration_sec,
                "mock_workloads": args.mock_workloads,
                "workload_mix": ["yolo_detection_loop", "fastapi_resnet18_concurrent_requests", "fastapi_whisper_transcription_burst"],
                "external_sensor_dependency": False,
            },
            "workloads": {
                "yolo_detection": {"model": args.yolo_model, "device": args.yolo_device, "interval_s": args.yolo_interval_sec, "imgsz": args.yolo_imgsz, "confidence_threshold": args.yolo_conf, "setup": yolo_metadata},
                "fastapi_resnet18": {"endpoint": RESNET_ENDPOINT, "concurrency": args.fastapi_concurrency, "interval_s": args.fastapi_interval_sec, "input": {"source": "synthetic_random_tensor", "shape": [args.batch_size, 3, args.height, args.width], "dtype": "float32", "seed": args.seed}},
                "fastapi_whisper": {"endpoint": WHISPER_ENDPOINT, "start_s": args.whisper_start_sec, "repeat": args.whisper_repeat, "interval_s": args.whisper_interval_sec, "audio_path": args.audio_path, "expected_text": args.expected_text, "language": args.language},
            },
            "metrics": {"before": metrics_before, "after": metrics_after},
            "serving_observability": serving_observability,
            "timeline": events,
            "summary_by_workload": summary,
            "interaction": interaction_summary(events),
            "interpretation": {"runtime_reliability_evidence": True, "deployment_ready_claim": False, "production_stress_test_claim": False, "accuracy_claim": False, "notes": "Sustained multi-workload behavior must be interpreted with telemetry, workload mix, backend/provider, duration, and power mode context."},
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
