#!/usr/bin/env python3
# YOLO object detection smoke benchmark for Jetson internal evidence.
# This is not an accuracy benchmark and does not use external camera/sensor input.

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "yolov8n.pt"


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


def package_asset_image() -> tuple[Path, str]:
    import ultralytics

    asset = Path(ultralytics.__file__).resolve().parent / "assets" / "bus.jpg"
    if not asset.exists():
        raise FileNotFoundError(f"ultralytics sample image not found: {asset}")
    return asset, "[site-packages]/ultralytics/assets/bus.jpg"


def resolve_model(model_name: str, allow_download: bool) -> Path:
    model_dir = ROOT / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / model_name
    if model_path.exists():
        return model_path
    if not allow_download:
        raise FileNotFoundError(
            f"{model_path} not found. Set YOLO_ALLOW_DOWNLOAD=1 to allow the runner to download the small YOLO smoke model."
        )

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


def cuda_metadata(torch: Any) -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"available": False}
    device_index = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(device_index)
    return {
        "available": True,
        "device_index": device_index,
        "device_name": torch.cuda.get_device_name(device_index),
        "capability": list(torch.cuda.get_device_capability(device_index)),
        "total_memory_bytes": props.total_memory,
    }


def detection_preview(result: Any, limit: int = 10) -> list[dict[str, Any]]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    classes = boxes.cls.detach().cpu().tolist()
    confs = boxes.conf.detach().cpu().tolist()
    xyxy = boxes.xyxy.detach().cpu().tolist()
    names = result.names
    rows = []
    for cls_id, conf, coords in list(zip(classes, confs, xyxy))[:limit]:
        class_id = int(cls_id)
        class_name = str(names.get(class_id, class_id)) if isinstance(names, dict) else str(class_id)
        rows.append({
            "class_id": class_id,
            "class_name": class_name,
            "confidence": round(float(conf), 6),
            "xyxy": [round(float(v), 3) for v in coords],
        })
    return rows


def build_report(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    result = payload["result"]
    latency = result["latency"]
    detections = result["output"]["detections_preview"]
    class_counts = result["output"]["class_counts"]
    lines = [
        "# YOLO Object Detection Smoke Report",
        "",
        "> YOLOv8n file-image object detection path를 Jetson 내부에서 실행한 optional extension evidence입니다.",
        "> Ultralytics package sample image와 pretrained smoke model을 사용하므로 broad accuracy evidence가 아니라 local detection pipeline evidence입니다.",
        "",
        "## Run Information",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {meta['generated_at']} |",
        f"| Hostname | `{meta['hostname']}` |",
        f"| Conda env | `{meta['conda_env']}` |",
        f"| Result schema | `{meta['schema_version']}` |",
        f"| Tegrastats log | `{meta['tegrastats_log']}` |",
        "",
        "## Model / Input",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | {result['model']['name']} |",
        f"| Model path | `{result['model']['path']}` |",
        f"| Model sha256 | `{result['model']['sha256']}` |",
        f"| Backend | {result['backend']} |",
        f"| Precision | {result['precision']} |",
        f"| Image | `{result['input']['path']}` |",
        f"| Image sha256 | `{result['input']['sha256']}` |",
        f"| Image size | {result['input']['width']}x{result['input']['height']} |",
        f"| Image source | {result['input']['source']} |",
        "",
        "## Latency",
        "",
        "| Metric | Value ms |",
        "|---|---:|",
        f"| Warmup | {result['runtime']['warmup']} runs |",
        f"| Repeat | {result['runtime']['repeat']} runs |",
        f"| Mean | {latency['mean_ms']} |",
        f"| P50 | {latency['p50_ms']} |",
        f"| P95 | {latency['p95_ms']} |",
        f"| P99 | {latency['p99_ms']} |",
        f"| Min | {latency['min_ms']} |",
        f"| Max | {latency['max_ms']} |",
        "",
        "## Detection Preview",
        "",
        f"- Detection count: {result['output']['detection_count']}",
        f"- Class counts: `{json.dumps(class_counts, sort_keys=True)}`",
        "",
        "| Class | Confidence | Box xyxy |",
        "|---|---:|---|",
    ]
    for item in detections[:10]:
        lines.append(f"| {item['class_name']} | {item['confidence']} | `{item['xyxy']}` |")
    if not detections:
        lines.append("| n/a | n/a | `[]` |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- This is file-image object detection smoke evidence, not production camera validation.",
        "- It does not use external cameras, sensors, microphones, motors, or robot hardware.",
        "- It does not claim broad object detection accuracy or deployment readiness.",
        "- Backend, model hash, image hash, warmup/repeat, confidence threshold, and image size are recorded for reproducibility.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run YOLO file-image object detection smoke benchmark.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--repeat", type=int, default=20)
    parser.add_argument("--tegrastats-log", default="")
    args = parser.parse_args()

    import torch
    import ultralytics
    from PIL import Image
    from ultralytics import YOLO

    if args.device == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device_name = args.device
    if device_name == "cuda" and not torch.cuda.is_available():
        raise SystemExit("requested CUDA but torch.cuda.is_available() is False")

    allow_download = os.environ.get("YOLO_ALLOW_DOWNLOAD", "0") == "1"
    model_path = resolve_model(args.model_name, allow_download=allow_download)
    if args.image is None:
        image_path, display_image_path = package_asset_image()
        image_source = "ultralytics_package_sample_image"
    else:
        image_path = args.image.resolve()
        display_image_path = str(args.image)
        image_source = "repo_or_user_file_image"
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as image:
        image_width, image_height = image.size

    model = YOLO(str(model_path))
    for _ in range(args.warmup):
        model.predict(source=str(image_path), device=device_name, imgsz=args.imgsz, conf=args.conf, verbose=False)
        if device_name == "cuda":
            torch.cuda.synchronize()

    samples_ms: list[float] = []
    last_result = None
    for _ in range(args.repeat):
        start = time.perf_counter()
        prediction = model.predict(source=str(image_path), device=device_name, imgsz=args.imgsz, conf=args.conf, verbose=False)
        if device_name == "cuda":
            torch.cuda.synchronize()
        samples_ms.append((time.perf_counter() - start) * 1000.0)
        last_result = prediction[0]
    assert last_result is not None

    preview = detection_preview(last_result)
    class_counts: dict[str, int] = {}
    for item in preview:
        class_counts[item["class_name"]] = class_counts.get(item["class_name"], 0) + 1

    payload = {
        "metadata": {
            "schema_version": "yolo-detection-smoke-v1",
            "generated_at": now_iso(),
            "hostname": "jetson-orin-nano",
            "platform": platform.platform(),
            "python_executable": "[conda-env]/bin/python3",
            "python_version": platform.python_version(),
            "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "git_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "git_status": safe_git_status(),
            "power_mode": run_command(["nvpmodel", "-q"]),
            "tegrastats_log": args.tegrastats_log or "not captured",
        },
        "result": {
            "task": "object_detection_smoke",
            "framework": "ultralytics",
            "backend": device_name,
            "precision": "fp32",
            "model": {
                "name": args.model_name,
                "architecture": "yolov8n",
                "path": str(model_path.relative_to(ROOT)),
                "sha256": sha256_file(model_path),
                "package": "ultralytics",
                "package_version": ultralytics.__version__,
                "weights": "pretrained_yolo_smoke_model_no_accuracy_claim",
            },
            "input": {
                "source": image_source,
                "path": display_image_path,
                "sha256": sha256_file(image_path),
                "format": image_path.suffix.lstrip(".").lower(),
                "width": image_width,
                "height": image_height,
                "external_sensor_dependency": False,
            },
            "runtime": {
                "torch_version": torch.__version__,
                "cuda": cuda_metadata(torch),
                "warmup": args.warmup,
                "repeat": args.repeat,
                "imgsz": args.imgsz,
                "confidence_threshold": args.conf,
                "preprocessing_included": True,
                "postprocessing_included": True,
            },
            "latency": summarize(samples_ms),
            "output": {
                "detection_count": len(last_result.boxes) if last_result.boxes is not None else 0,
                "class_counts": class_counts,
                "detections_preview": preview,
            },
            "interpretation": {
                "accuracy_claim": False,
                "deployment_ready_claim": False,
                "external_camera_dependency": False,
                "notes": "File-image object detection smoke validates local YOLO inference plumbing only.",
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
