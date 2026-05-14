"""InferEdge-compatible evidence schema helpers.

This module intentionally keeps a small, explicit compatibility surface:
- `metadata.json` follows the Forge-style provenance envelope.
- `result.json` preserves InferEdgeRuntime/Lab-compatible top-level fields while
  embedding this project's runtime-comparison evidence under `comparison` and `extra`.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METADATA_SCHEMA_VERSION = "0.1.0"
RESULT_SCHEMA_VERSION = "inferedge-runtime-result-v1"
EXPORT_SCHEMA_VERSION = "inferedge-internal-lab-export-v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _relative_or_original(path_text: str, root: Path) -> str:
    path = Path(path_text)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return path_text


def summarize_tegrastats(log_path: Path) -> dict[str, Any]:
    if not log_path:
        return {"status": "not_provided", "sample_count": 0}
    if not log_path.exists():
        return {"status": "unavailable", "sample_count": 0, "path": str(log_path)}

    ram_used: list[float] = []
    ram_total: list[float] = []
    temps: list[tuple[str, float]] = []
    vdd_in: list[float] = []
    for line in log_path.read_text(errors="replace").splitlines():
        ram_match = re.search(r"RAM\s+(\d+)/(\d+)MB", line)
        if ram_match:
            ram_used.append(float(ram_match.group(1)))
            ram_total.append(float(ram_match.group(2)))
        for name, value in re.findall(r"([A-Za-z0-9_]+)@([0-9.]+)C", line):
            temps.append((name, float(value)))
        power_match = re.search(r"VDD_IN\s+(\d+)mW", line)
        if power_match:
            vdd_in.append(float(power_match.group(1)))

    if not (ram_used or temps or vdd_in):
        return {"status": "no_samples", "sample_count": 0, "path": str(log_path)}

    max_temp_name = ""
    max_temp_c = 0.0
    if temps:
        max_temp_name, max_temp_c = max(temps, key=lambda item: item[1])

    return {
        "status": "parsed",
        "sample_count": max(len(ram_used), len(vdd_in), len(temps)),
        "ram_used_mb_avg": round(sum(ram_used) / len(ram_used), 3) if ram_used else 0.0,
        "ram_used_mb_max": max(ram_used) if ram_used else 0.0,
        "ram_total_mb": max(ram_total) if ram_total else 0.0,
        "max_temp_c": max_temp_c,
        "max_temp_name": max_temp_name,
        "vdd_in_mw_avg": round(sum(vdd_in) / len(vdd_in), 3) if vdd_in else 0.0,
        "vdd_in_mw_max": max(vdd_in) if vdd_in else 0.0,
    }


def build_inferedge_export(runtime_compare_path: Path, output_dir: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    comparison = read_json(runtime_compare_path)
    result = comparison["result"]
    metadata = comparison["metadata"]
    runtimes = {runtime["name"]: runtime for runtime in result["runtimes"]}
    baseline = runtimes["pytorch_cuda"]
    candidate = runtimes["tensorrt_trtexec"]
    latency = candidate["latency_ms"]
    input_shape = candidate["input_shape"]
    batch, _channels, height, width = input_shape
    power_mode = metadata.get("power_mode", {}).get("stdout", "unknown").replace("\n", "; ") or "unknown"
    timestamp = now_iso()
    compare_key = f"resnet18__b{batch}__h{height}w{width}__{candidate['precision']}"
    backend_key = "tensorrt__jetson"
    engine_path = Path(candidate["engine_path"])
    onnx_path = Path(candidate["onnx_path"])
    runtime_compare_text = _relative_or_original(str(runtime_compare_path), repo_root)
    result_json_text = _relative_or_original(str(output_dir / "result.json"), repo_root)
    engine_path_text = _relative_or_original(str(engine_path), repo_root)
    onnx_path_text = _relative_or_original(str(onnx_path), repo_root)
    tegrastats_path = Path(read_json(Path(candidate["source_json"]))["metadata"].get("tegrastats_note", ""))
    tegrastats_path_text = _relative_or_original(str(tegrastats_path), repo_root) if tegrastats_path else ""
    tegrastats_summary = summarize_tegrastats(tegrastats_path)

    result_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "compare_key": compare_key,
        "backend_key": backend_key,
        "runtime_role": "runtime-result",
        "manifest_path": "",
        "manifest_applied": False,
        "model_name": onnx_path.name,
        "model_path": onnx_path_text,
        "engine_name": "tensorrt",
        "engine_backend": "tensorrt",
        "device_name": "jetson",
        "batch": batch,
        "height": height,
        "width": width,
        "warmup": 500,
        "runs": candidate["repeat_or_iterations"],
        "mean_ms": latency["mean"],
        "p50_ms": latency["p50"],
        "p95_ms": latency["p95"],
        "p99_ms": latency["p99"],
        "fps_value": candidate.get("throughput_qps"),
        "success": True,
        "status": "success",
        "model": {"path": onnx_path_text, "name": onnx_path.name, "sha256": candidate["onnx_sha256"]},
        "engine": {
            "name": "tensorrt",
            "backend": "tensorrt",
            "available": True,
            "status_message": "TensorRT trtexec FP16 smoke completed.",
            "path": engine_path_text,
            "sha256": candidate["engine_sha256"],
        },
        "device": {"name": "jetson", "hostname": socket.gethostname()},
        "precision": candidate["precision"],
        "run_config": {
            "batch": batch,
            "height": height,
            "width": width,
            "warmup": 500,
            "warmup_unit": "ms",
            "runs": candidate["repeat_or_iterations"],
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_path_text,
            "manifest_path": "",
            "manifest_applied": False,
            "source_runtime_compare_json": runtime_compare_text,
        },
        "latency_ms": {
            "mean": latency["mean"],
            "min": latency["min"],
            "max": latency["max"],
            "std": None,
            "p50": latency["p50"],
            "p90": None,
            "p95": latency["p95"],
            "p99": latency["p99"],
            "samples": [],
        },
        "fps": candidate.get("throughput_qps"),
        "benchmark": {"success": True, "status": "success", "message": "runtime comparison exported to InferEdge-compatible result"},
        "timestamp": timestamp,
        "system": {
            "os": platform.system().lower(),
            "machine": platform.machine(),
            "jetson": {
                "power_mode": power_mode,
                "jetson_clocks": "unknown",
                "tegrastats_log_path": tegrastats_path_text,
            },
        },
        "jetson_evidence": {
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_path_text,
            "tegrastats_summary": tegrastats_summary,
        },
        "model_metadata": {
            "inputs": [{"name": "input", "element_type": "float32", "shape": input_shape}],
            "outputs": [{"name": "output", "element_type": "float32", "shape": [batch, 1000]}],
        },
        "comparison": {
            "source_json": runtime_compare_text,
            "comparison_name": result["comparison_name"],
            "verdict": result["comparability"]["verdict"],
            "comparability": result["comparability"],
            "baseline_runtime": baseline,
            "candidate_runtime": candidate,
            "ratios": result["ratios"],
        },
        "extra": {
            "runtime": "jetson-orin-nano-internal-lab",
            "json_export": "enabled",
            "output_mode": "explicit",
            "latest_path": result_json_text,
            "manifest_recorded": False,
            "manifest_precision": candidate["precision"],
            "manifest_format": "onnx+engine",
            "input_mode": "synthetic",
            "input_path": "",
            "input_preprocess": "synthetic_random_tensor_no_preprocess",
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_path_text,
            "tegrastats_status": tegrastats_summary.get("status", "unknown"),
            "compare_ready": True,
            "compare_key": compare_key,
            "backend_key": backend_key,
            "compare_model_source": "runtime_comparison_source_model",
            "compare_model_name": "resnet18",
            "export_schema_version": EXPORT_SCHEMA_VERSION,
        },
    }

    metadata_json = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_model": {"format": "onnx", "path": onnx_path_text, "sha256": candidate["onnx_sha256"]},
        "artifacts": [
            {"role": "deployment_model", "format": "engine", "path": engine_path_text, "sha256": candidate["engine_sha256"]},
            {"role": "runtime_result", "format": "json", "path": result_json_text, "sha256": "__FILLED_AFTER_WRITE__"},
            {"role": "runtime_comparison", "format": "json", "path": runtime_compare_text, "sha256": sha256_file(runtime_compare_path)},
        ],
        "build": {
            "build_id": f"resnet18-tensorrt-fp16-{timestamp.replace(':', '').replace('-', '')}",
            "backend": "tensorrt",
            "target": "jetson",
            "preset_name": "tensorrt/jetson_fp16_smoke",
            "timestamp": timestamp,
        },
        "handoff": {"consumer": "InferEdgeLab", "ready": True},
        "lab_compat": {
            "profile_ready": True,
            "runtime": {
                "device": "jetson",
                "engine": "tensorrt",
                "engine_path": engine_path_text,
                "precision": candidate["precision"],
                "requested_batch": batch,
                "requested_height": height,
                "requested_width": width,
                "runtime_artifact_path": engine_path_text,
                "result_json_path": result_json_text,
            },
        },
        "preset_snapshot": {
            "name": "tensorrt/jetson_fp16_smoke",
            "backend": "tensorrt",
            "target": "jetson",
            "build_options": {"precision": candidate["precision"], "input_shape": input_shape, "measurement": "trtexec"},
            "metadata": {"validation_handoff": "inferedgelab", "source": "jetson-orin-nano-internal-lab"},
        },
        "export": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "source_runtime_compare_json": runtime_compare_text,
            "repo_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "repo_status": run_command(["git", "status", "--short", "--branch"]),
        },
    }
    return metadata_json, result_json


def _path_from_repo(path_text: str, repo_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root / path


def _sha256_if_exists(path_text: str, repo_root: Path) -> str:
    path = _path_from_repo(path_text, repo_root)
    if path.exists() and path.is_file():
        return sha256_file(path)
    return ""


def _path_from_sanitized(path_text: str, repo_root: Path) -> Path:
    if path_text.startswith("[home]/"):
        return Path.home() / path_text[len("[home]/"):]
    return _path_from_repo(path_text, repo_root)


def _sha256_sanitized_if_exists(path_text: str, repo_root: Path) -> str:
    path = _path_from_sanitized(path_text, repo_root)
    if path.exists() and path.is_file():
        return sha256_file(path)
    return ""


def build_inferedge_serving_export(fastapi_smoke_path: Path, output_dir: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build InferEdge-compatible metadata/result pair for FastAPI serving evidence."""

    smoke = read_json(fastapi_smoke_path)
    metadata = smoke["metadata"]
    serving_result = smoke["result"]
    model = serving_result["model"]
    input_info = serving_result["input"]
    client_latency = serving_result["latency"]["client_roundtrip_ms"]
    server_latency = serving_result["latency"]["server_inference_ms"]
    batch, _channels, height, width = input_info["shape"]
    backend = serving_result["backend"]
    precision = serving_result["precision"]
    power_mode = metadata.get("power_mode", {}).get("stdout", "unknown").replace("\n", "; ") or "unknown"
    timestamp = now_iso()
    compare_key = f"resnet18__fastapi__b{batch}__h{height}w{width}__{precision}"
    backend_key = f"fastapi_pytorch_{backend}__jetson"
    source_text = _relative_or_original(str(fastapi_smoke_path), repo_root)
    result_json_text = _relative_or_original(str(output_dir / "result.json"), repo_root)
    server_log_text = metadata.get("server_log", "")
    tegrastats_text = metadata.get("tegrastats_log", "")
    server_app_text = "src/server/resnet18_app.py"
    tegrastats_summary = summarize_tegrastats(_path_from_repo(tegrastats_text, repo_root)) if tegrastats_text else {"status": "not_provided", "sample_count": 0}
    fps_value = round(1000.0 / client_latency["mean_ms"], 4) if client_latency.get("mean_ms") else None

    result_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "compare_key": compare_key,
        "backend_key": backend_key,
        "runtime_role": "serving-result",
        "manifest_path": "",
        "manifest_applied": False,
        "model_name": model["id"],
        "model_path": "generated:torchvision.models.resnet18(weights=None, seed=42)",
        "engine_name": "fastapi",
        "engine_backend": "fastapi+pytorch",
        "device_name": "jetson",
        "batch": batch,
        "height": height,
        "width": width,
        "warmup": serving_result["runtime"]["warmup"],
        "runs": serving_result["runtime"]["repeat"],
        "mean_ms": client_latency["mean_ms"],
        "p50_ms": client_latency["p50_ms"],
        "p95_ms": client_latency["p95_ms"],
        "p99_ms": client_latency["p99_ms"],
        "fps_value": fps_value,
        "success": True,
        "status": "success",
        "model": {
            "path": "generated:torchvision.models.resnet18(weights=None, seed=42)",
            "name": model["architecture"],
            "sha256": model["state_dict_sha256"],
            "weights": model["weights"],
        },
        "engine": {
            "name": "fastapi",
            "backend": "fastapi+pytorch",
            "available": True,
            "status_message": "FastAPI localhost ResNet18 synthetic inference smoke completed.",
            "path": server_app_text,
            "sha256": _sha256_if_exists(server_app_text, repo_root),
        },
        "device": {"name": "jetson", "hostname": metadata.get("hostname", "jetson-orin-nano")},
        "precision": precision,
        "run_config": {
            "batch": batch,
            "height": height,
            "width": width,
            "warmup": serving_result["runtime"]["warmup"],
            "runs": serving_result["runtime"]["repeat"],
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "base_url": serving_result["server"]["base_url"],
            "endpoint": serving_result["server"]["endpoint"],
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "manifest_path": "",
            "manifest_applied": False,
            "source_fastapi_smoke_json": source_text,
        },
        "latency_ms": {
            "mean": client_latency["mean_ms"],
            "min": client_latency["min_ms"],
            "max": client_latency["max_ms"],
            "std": None,
            "p50": client_latency["p50_ms"],
            "p90": None,
            "p95": client_latency["p95_ms"],
            "p99": client_latency["p99_ms"],
            "samples": client_latency["samples_ms"],
        },
        "fps": fps_value,
        "benchmark": {"success": True, "status": "success", "message": "FastAPI serving smoke exported to InferEdge-compatible result"},
        "timestamp": timestamp,
        "system": {
            "os": platform.system().lower(),
            "machine": platform.machine(),
            "jetson": {
                "power_mode": power_mode,
                "jetson_clocks": "unknown",
                "tegrastats_log_path": tegrastats_text,
            },
        },
        "jetson_evidence": {
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_summary": tegrastats_summary,
        },
        "model_metadata": {
            "inputs": [{"name": "synthetic", "element_type": input_info["dtype"], "shape": input_info["shape"]}],
            "outputs": [{"name": "logits", "element_type": "float32", "shape": serving_result["output"]["output_shape"]}],
        },
        "comparison": {
            "source_json": source_text,
            "comparison_name": "fastapi_serving_layer_smoke",
            "verdict": "serving_layer_evidence_not_direct_regression",
            "comparability": {
                "same_model_hash": True,
                "same_input_shape": True,
                "same_precision": True,
                "same_backend": False,
                "note": "serving result separates localhost client roundtrip and server-side PyTorch inference latency",
            },
            "ratios": {},
        },
        "serving": {
            "source_json": source_text,
            "framework": serving_result["server"]["framework"],
            "asgi": serving_result["server"]["asgi"],
            "base_url": serving_result["server"]["base_url"],
            "endpoint": serving_result["server"]["endpoint"],
            "health": serving_result["server"]["health"],
            "request": {
                "source": input_info["source"],
                "shape": input_info["shape"],
                "dtype": input_info["dtype"],
                "seed": input_info["seed"],
            },
            "latency_layers": {
                "client_roundtrip_ms": client_latency,
                "server_inference_ms": server_latency,
            },
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
        },
        "extra": {
            "runtime": "jetson-orin-nano-internal-lab",
            "json_export": "enabled",
            "output_mode": "explicit",
            "latest_path": result_json_text,
            "manifest_recorded": False,
            "manifest_precision": precision,
            "manifest_format": "fastapi+pytorch",
            "input_mode": "synthetic",
            "input_path": "",
            "input_preprocess": "synthetic_random_tensor_no_preprocess",
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_status": tegrastats_summary.get("status", "unknown"),
            "compare_ready": True,
            "serving_ready": True,
            "compare_key": compare_key,
            "backend_key": backend_key,
            "compare_model_source": "fastapi_serving_source_model",
            "compare_model_name": "resnet18",
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "evidence_kind": "serving_layer_smoke",
        },
    }

    metadata_json = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_model": {
            "format": "pytorch_state_dict",
            "path": "generated:torchvision.models.resnet18(weights=None, seed=42)",
            "sha256": model["state_dict_sha256"],
        },
        "artifacts": [
            {"role": "runtime_result", "format": "json", "path": result_json_text, "sha256": "__FILLED_AFTER_WRITE__"},
            {"role": "serving_smoke_result", "format": "json", "path": source_text, "sha256": sha256_file(fastapi_smoke_path)},
            {"role": "server_log", "format": "log", "path": server_log_text, "sha256": _sha256_if_exists(server_log_text, repo_root)},
            {"role": "tegrastats_log", "format": "log", "path": tegrastats_text, "sha256": _sha256_if_exists(tegrastats_text, repo_root)},
        ],
        "build": {
            "build_id": f"resnet18-fastapi-serving-{timestamp.replace(':', '').replace('-', '')}",
            "backend": "fastapi+pytorch",
            "target": "jetson",
            "preset_name": "fastapi/jetson_resnet18_smoke",
            "timestamp": timestamp,
        },
        "handoff": {"consumer": "InferEdgeLab", "ready": True},
        "lab_compat": {
            "profile_ready": True,
            "runtime": {
                "device": "jetson",
                "engine": "fastapi+pytorch",
                "engine_path": server_app_text,
                "precision": precision,
                "requested_batch": batch,
                "requested_height": height,
                "requested_width": width,
                "runtime_artifact_path": server_app_text,
                "result_json_path": result_json_text,
            },
        },
        "preset_snapshot": {
            "name": "fastapi/jetson_resnet18_smoke",
            "backend": "fastapi+pytorch",
            "target": "jetson",
            "build_options": {
                "precision": precision,
                "input_shape": input_info["shape"],
                "measurement": "localhost_http_client_roundtrip_and_server_inference",
            },
            "metadata": {"validation_handoff": "inferedgelab", "source": "jetson-orin-nano-internal-lab"},
        },
        "export": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "source_fastapi_smoke_json": source_text,
            "repo_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "repo_status": run_command(["git", "status", "--short", "--branch"]),
        },
    }
    return metadata_json, result_json


def build_inferedge_whisper_serving_export(fastapi_whisper_smoke_path: Path, output_dir: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build InferEdge-compatible metadata/result pair for FastAPI Whisper serving evidence."""

    smoke = read_json(fastapi_whisper_smoke_path)
    metadata = smoke["metadata"]
    serving_result = smoke["result"]
    if serving_result.get("success") is not True or serving_result.get("status") != "succeeded":
        raise ValueError(
            "FastAPI Whisper serving smoke must be successful before InferEdge export: "
            f"status={serving_result.get('status')!r}, success={serving_result.get('success')!r}"
        )
    model = serving_result["model"]
    audio = serving_result["input"]
    transcription = serving_result["transcription"]
    client_latency = serving_result["latency"]["client_roundtrip_ms"]
    server_latency = serving_result["latency"]["server_inference_ms"]
    backend = serving_result["backend"]
    precision = serving_result["precision"]
    power_mode = metadata.get("power_mode", {}).get("stdout", "unknown").replace("\n", "; ") or "unknown"
    timestamp = now_iso()
    model_name = model["id"]
    source_text = _relative_or_original(str(fastapi_whisper_smoke_path), repo_root)
    result_json_text = _relative_or_original(str(output_dir / "result.json"), repo_root)
    server_log_text = metadata.get("server_log", "")
    tegrastats_text = metadata.get("tegrastats_log", "")
    server_app_text = "src/server/resnet18_app.py"
    tegrastats_summary = summarize_tegrastats(_path_from_repo(tegrastats_text, repo_root)) if tegrastats_text else {"status": "not_provided", "sample_count": 0}
    duration_s = audio["duration_s"]
    audio_seconds_per_client_second = round(duration_s / (client_latency["mean_ms"] / 1000.0), 4) if client_latency.get("mean_ms") else None
    audio_seconds_per_server_second = round(duration_s / (server_latency["mean_ms"] / 1000.0), 4) if server_latency.get("mean_ms") else None
    compare_key = f"{model_name}__fastapi_speech__{audio['sample_rate_hz']}hz__{backend}"
    backend_key = f"fastapi_openai_whisper_{backend}__jetson"
    normalized_contains_expected = bool(transcription.get("normalized_contains_expected"))

    result_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "compare_key": compare_key,
        "backend_key": backend_key,
        "runtime_role": "serving-result",
        "manifest_path": "",
        "manifest_applied": False,
        "model_name": model_name,
        "model_path": "python-package:openai-whisper",
        "engine_name": "fastapi-whisper",
        "engine_backend": "fastapi+openai-whisper",
        "device_name": "jetson",
        "batch": 1,
        "height": 0,
        "width": 0,
        "warmup": serving_result["runtime"]["warmup"],
        "runs": serving_result["runtime"]["repeat"],
        "mean_ms": client_latency["mean_ms"],
        "p50_ms": client_latency["p50_ms"],
        "p95_ms": client_latency["p95_ms"],
        "p99_ms": client_latency["p99_ms"],
        "fps_value": audio_seconds_per_client_second,
        "success": True,
        "status": "success",
        "model": {
            "path": "python-package:openai-whisper",
            "name": model_name,
            "family": model.get("architecture", "whisper"),
            "sha256": "",
            "cache_present": model.get("model_cache_present", False),
        },
        "engine": {
            "name": "fastapi-whisper",
            "backend": "fastapi+openai-whisper",
            "available": True,
            "status_message": "FastAPI localhost Whisper speech transcription smoke completed.",
            "path": server_app_text,
            "sha256": _sha256_if_exists(server_app_text, repo_root),
        },
        "device": {"name": "jetson", "hostname": metadata.get("hostname", "jetson-orin-nano")},
        "precision": precision,
        "run_config": {
            "batch": 1,
            "height": 0,
            "width": 0,
            "warmup": serving_result["runtime"]["warmup"],
            "runs": serving_result["runtime"]["repeat"],
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "base_url": serving_result["server"]["base_url"],
            "endpoint": serving_result["server"]["endpoint"],
            "audio_path": audio["path"],
            "audio_source": audio["source"],
            "expected_text": transcription.get("expected_text", ""),
            "language": transcription.get("language", "en"),
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "manifest_path": "",
            "manifest_applied": False,
            "source_fastapi_whisper_smoke_json": source_text,
        },
        "latency_ms": {
            "mean": client_latency["mean_ms"],
            "min": client_latency["min_ms"],
            "max": client_latency["max_ms"],
            "std": None,
            "p50": client_latency["p50_ms"],
            "p90": None,
            "p95": client_latency["p95_ms"],
            "p99": client_latency["p99_ms"],
            "samples": client_latency["samples_ms"],
        },
        "fps": audio_seconds_per_client_second,
        "benchmark": {"success": True, "status": "success", "message": "FastAPI Whisper serving smoke exported to InferEdge-compatible result"},
        "timestamp": timestamp,
        "system": {
            "os": platform.system().lower(),
            "machine": platform.machine(),
            "jetson": {
                "power_mode": power_mode,
                "jetson_clocks": "unknown",
                "tegrastats_log_path": tegrastats_text,
            },
        },
        "jetson_evidence": {
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_summary": tegrastats_summary,
        },
        "model_metadata": {
            "inputs": [{
                "name": "audio",
                "element_type": "pcm_s16le",
                "shape": [audio["frames"], audio["channels"]],
                "sample_rate_hz": audio["sample_rate_hz"],
                "duration_s": duration_s,
            }],
            "outputs": [{"name": "transcript", "element_type": "utf8_text", "shape": [1]}],
        },
        "comparison": {
            "source_json": source_text,
            "comparison_name": "fastapi_whisper_serving_layer_smoke",
            "verdict": "serving_layer_evidence_not_direct_regression",
            "comparability": {
                "same_model_hash": False,
                "same_input_shape": True,
                "same_precision": True,
                "same_backend": True,
                "note": "serving result validates localhost HTTP plus Whisper transcription plumbing; it is not a broad speech accuracy benchmark or deployment approval",
            },
            "ratios": {
                "audio_seconds_per_client_second": audio_seconds_per_client_second,
                "audio_seconds_per_server_second": audio_seconds_per_server_second,
            },
        },
        "serving": {
            "source_json": source_text,
            "framework": serving_result["server"]["framework"],
            "asgi": serving_result["server"]["asgi"],
            "base_url": serving_result["server"]["base_url"],
            "endpoint": serving_result["server"]["endpoint"],
            "health": serving_result["server"]["health"],
            "request": {
                "source": audio["source"],
                "audio_path": audio["path"],
                "audio_sha256": audio["sha256"],
                "sample_rate_hz": audio["sample_rate_hz"],
                "channels": audio["channels"],
                "duration_s": duration_s,
                "expected_text": transcription.get("expected_text", ""),
                "language": transcription.get("language", "en"),
            },
            "latency_layers": {
                "client_roundtrip_ms": client_latency,
                "server_transcription_ms": server_latency,
            },
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
        },
        "audio": {
            "path": audio["path"],
            "sha256": audio["sha256"],
            "source": audio["source"],
            "sample_rate_hz": audio["sample_rate_hz"],
            "channels": audio["channels"],
            "duration_s": duration_s,
            "format": audio["format"],
        },
        "transcription": {
            "text": transcription["text"],
            "expected_text": transcription.get("expected_text", ""),
            "language": transcription.get("language", "en"),
            "normalized_contains_expected": normalized_contains_expected,
            "segments": transcription.get("segments", []),
        },
        "extra": {
            "runtime": "jetson-orin-nano-internal-lab",
            "json_export": "enabled",
            "output_mode": "explicit",
            "latest_path": result_json_text,
            "manifest_recorded": False,
            "manifest_precision": precision,
            "manifest_format": "fastapi+openai-whisper",
            "input_mode": "license_clear_generated_speech",
            "input_path": audio["path"],
            "input_preprocess": "repo_relative_wav_path_validated_by_fastapi",
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "server_log_path": server_log_text,
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_status": tegrastats_summary.get("status", "unknown"),
            "compare_ready": True,
            "serving_ready": True,
            "transcription_ready": True,
            "expected_text_matched": normalized_contains_expected,
            "compare_key": compare_key,
            "backend_key": backend_key,
            "compare_model_source": "fastapi_whisper_serving_source_model",
            "compare_model_name": model_name,
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "evidence_kind": "fastapi_audio_serving_smoke",
            "accuracy_claim": False,
            "deployment_ready_claim": False,
        },
    }

    metadata_json = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_model": {"format": "openai-whisper-package", "path": "python-package:openai-whisper", "sha256": ""},
        "artifacts": [
            {"role": "runtime_result", "format": "json", "path": result_json_text, "sha256": "__FILLED_AFTER_WRITE__"},
            {"role": "fastapi_whisper_serving_smoke", "format": "json", "path": source_text, "sha256": sha256_file(fastapi_whisper_smoke_path)},
            {"role": "audio_input", "format": "wav", "path": audio["path"], "sha256": audio["sha256"]},
            {"role": "server_log", "format": "log", "path": server_log_text, "sha256": _sha256_if_exists(server_log_text, repo_root)},
            {"role": "tegrastats_log", "format": "log", "path": tegrastats_text, "sha256": _sha256_if_exists(tegrastats_text, repo_root)},
        ],
        "build": {
            "build_id": f"fastapi-whisper-serving-{timestamp.replace(':', '').replace('-', '')}",
            "backend": "fastapi+openai-whisper",
            "target": "jetson",
            "preset_name": "fastapi/jetson_whisper_speech_smoke",
            "timestamp": timestamp,
        },
        "handoff": {"consumer": "InferEdgeLab", "ready": True},
        "lab_compat": {
            "profile_ready": True,
            "runtime": {
                "device": "jetson",
                "engine": "fastapi+openai-whisper",
                "engine_path": server_app_text,
                "precision": precision,
                "requested_batch": 1,
                "requested_height": 0,
                "requested_width": 0,
                "runtime_artifact_path": server_app_text,
                "result_json_path": result_json_text,
            },
        },
        "preset_snapshot": {
            "name": "fastapi/jetson_whisper_speech_smoke",
            "backend": "fastapi+openai-whisper",
            "target": "jetson",
            "build_options": {
                "precision": precision,
                "model": model_name,
                "endpoint": serving_result["server"]["endpoint"],
                "audio_sample_rate_hz": audio["sample_rate_hz"],
                "measurement": "localhost_http_client_roundtrip_and_server_transcription",
            },
            "metadata": {"validation_handoff": "inferedgelab", "source": "jetson-orin-nano-internal-lab"},
        },
        "export": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "source_fastapi_whisper_smoke_json": source_text,
            "source_smoke_commit": metadata.get("git_commit", {}),
            "source_smoke_status": metadata.get("git_status", {}),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "export_workspace_status": run_command(["git", "status", "--short", "--branch"]),
            "artifact_commit_note": (
                "The commit containing this generated metadata is the git commit that tracks this file; "
                "it is intentionally not embedded to avoid self-referential commit hashes."
            ),
        },
    }
    return metadata_json, result_json


def build_inferedge_audio_export(whisper_smoke_path: Path, output_dir: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build InferEdge-compatible metadata/result pair for Whisper audio transcription evidence."""

    smoke = read_json(whisper_smoke_path)
    metadata = smoke["metadata"]
    evidence = smoke["result"]
    audio = evidence["audio"]
    model = evidence["model"]
    runtime = evidence["runtime"]
    latency = evidence["latency_ms"]
    transcription = evidence["transcription"]
    power_mode = metadata.get("power_mode", {}).get("stdout", "unknown").replace("\n", "; ") or "unknown"
    timestamp = now_iso()
    model_name = f"whisper-{model['name']}"
    backend = evidence["backend"]
    precision = evidence["precision"]
    source_text = _relative_or_original(str(whisper_smoke_path), repo_root)
    result_json_text = _relative_or_original(str(output_dir / "result.json"), repo_root)
    audio_path_text = audio["path"]
    tegrastats_text = metadata.get("tegrastats_note", "")
    tegrastats_summary = summarize_tegrastats(_path_from_repo(tegrastats_text, repo_root)) if tegrastats_text else {"status": "not_provided", "sample_count": 0}
    duration_s = audio["duration_s"]
    real_time_factor = runtime.get("real_time_factor")
    audio_seconds_per_second = round(duration_s / (latency["mean_ms"] / 1000.0), 4) if latency.get("mean_ms") else None
    compare_key = f"{model_name}__speech__{audio['sample_rate_hz']}hz__{backend}"
    backend_key = f"openai_whisper_{backend}__jetson"
    normalized_contains_expected = bool(transcription.get("normalized_contains_expected"))
    model_cache_path = model.get("cache_path", "")
    model_cache_sha256 = _sha256_sanitized_if_exists(model_cache_path, repo_root)

    result_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "compare_key": compare_key,
        "backend_key": backend_key,
        "runtime_role": "audio-transcription-result",
        "manifest_path": "",
        "manifest_applied": False,
        "model_name": model_name,
        "model_path": model_cache_path,
        "engine_name": "openai-whisper",
        "engine_backend": "openai-whisper",
        "device_name": "jetson",
        "batch": 1,
        "height": 0,
        "width": 0,
        "warmup": runtime["warmup"],
        "runs": runtime["repeat"],
        "mean_ms": latency["mean_ms"],
        "p50_ms": latency["p50_ms"],
        "p95_ms": latency["p95_ms"],
        "p99_ms": latency["p99_ms"],
        "fps_value": audio_seconds_per_second,
        "success": True,
        "status": "success",
        "model": {
            "path": model_cache_path,
            "name": model_name,
            "family": model["family"],
            "sha256": model_cache_sha256,
            "cache_present": model["cache_present"],
        },
        "engine": {
            "name": "openai-whisper",
            "backend": "openai-whisper",
            "available": metadata["package"]["available"],
            "status_message": "Whisper speech transcription smoke completed.",
            "path": "python-package:openai-whisper",
            "version": metadata["package"].get("version", ""),
            "sha256": "",
        },
        "device": {"name": "jetson", "hostname": metadata.get("hostname", "jetson-orin-nano")},
        "precision": precision,
        "run_config": {
            "batch": 1,
            "height": 0,
            "width": 0,
            "warmup": runtime["warmup"],
            "runs": runtime["repeat"],
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "audio_path": audio_path_text,
            "audio_source": audio["source"],
            "expected_text": transcription.get("expected_text", ""),
            "language": runtime["language"],
            "model_cache_path": model_cache_path,
            "tegrastats_log_path": tegrastats_text,
            "manifest_path": "",
            "manifest_applied": False,
            "source_whisper_smoke_json": source_text,
        },
        "latency_ms": {
            "mean": latency["mean_ms"],
            "min": latency["min_ms"],
            "max": latency["max_ms"],
            "std": None,
            "p50": latency["p50_ms"],
            "p90": None,
            "p95": latency["p95_ms"],
            "p99": latency["p99_ms"],
            "samples": latency["samples_ms"],
        },
        "fps": audio_seconds_per_second,
        "benchmark": {"success": True, "status": "success", "message": "Whisper transcription smoke exported to InferEdge-compatible result"},
        "timestamp": timestamp,
        "system": {
            "os": platform.system().lower(),
            "machine": platform.machine(),
            "jetson": {
                "power_mode": power_mode,
                "jetson_clocks": "unknown",
                "tegrastats_log_path": tegrastats_text,
            },
        },
        "jetson_evidence": {
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_summary": tegrastats_summary,
        },
        "model_metadata": {
            "inputs": [{
                "name": "audio",
                "element_type": "pcm_s16le",
                "shape": [audio["frames"], audio["channels"]],
                "sample_rate_hz": audio["sample_rate_hz"],
                "duration_s": duration_s,
            }],
            "outputs": [{"name": "transcript", "element_type": "utf8_text", "shape": [1]}],
        },
        "comparison": {
            "source_json": source_text,
            "comparison_name": "whisper_speech_transcription_smoke",
            "verdict": "audio_transcription_smoke_not_accuracy_benchmark",
            "comparability": {
                "same_model_hash": bool(model_cache_sha256),
                "same_input_shape": True,
                "same_precision": True,
                "same_backend": True,
                "note": "speech smoke validates a license-clear local transcription path; it is not a broad accuracy benchmark or deployment approval",
            },
            "ratios": {"real_time_factor": real_time_factor, "audio_seconds_per_second": audio_seconds_per_second},
        },
        "audio": {
            "path": audio_path_text,
            "sha256": audio["sha256"],
            "source": audio["source"],
            "sample_rate_hz": audio["sample_rate_hz"],
            "channels": audio["channels"],
            "duration_s": duration_s,
            "format": audio["format"],
        },
        "transcription": {
            "text": transcription["text"],
            "expected_text": transcription.get("expected_text", ""),
            "language": transcription.get("language", runtime["language"]),
            "normalized_contains_expected": normalized_contains_expected,
            "segments": transcription.get("segments", []),
        },
        "extra": {
            "runtime": "jetson-orin-nano-internal-lab",
            "json_export": "enabled",
            "output_mode": "explicit",
            "latest_path": result_json_text,
            "manifest_recorded": False,
            "manifest_precision": precision,
            "manifest_format": "openai-whisper",
            "input_mode": "license_clear_generated_speech",
            "input_path": audio_path_text,
            "input_preprocess": "ffmpeg_flite_generated_wav_16khz_mono",
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_status": tegrastats_summary.get("status", "unknown"),
            "compare_ready": True,
            "transcription_ready": True,
            "expected_text_matched": normalized_contains_expected,
            "compare_key": compare_key,
            "backend_key": backend_key,
            "compare_model_source": "whisper_model_cache",
            "compare_model_name": model_name,
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "evidence_kind": "audio_transcription_smoke",
            "accuracy_claim": False,
            "deployment_ready_claim": False,
        },
    }

    metadata_json = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_model": {"format": "openai-whisper-cache", "path": model_cache_path, "sha256": model_cache_sha256},
        "artifacts": [
            {"role": "runtime_result", "format": "json", "path": result_json_text, "sha256": "__FILLED_AFTER_WRITE__"},
            {"role": "whisper_smoke_result", "format": "json", "path": source_text, "sha256": sha256_file(whisper_smoke_path)},
            {"role": "audio_input", "format": "wav", "path": audio_path_text, "sha256": audio["sha256"]},
            {"role": "tegrastats_log", "format": "log", "path": tegrastats_text, "sha256": _sha256_if_exists(tegrastats_text, repo_root)},
        ],
        "build": {
            "build_id": f"whisper-speech-transcription-{timestamp.replace(':', '').replace('-', '')}",
            "backend": "openai-whisper",
            "target": "jetson",
            "preset_name": "whisper/jetson_speech_smoke",
            "timestamp": timestamp,
        },
        "handoff": {"consumer": "InferEdgeLab", "ready": True},
        "lab_compat": {
            "profile_ready": True,
            "runtime": {
                "device": "jetson",
                "engine": "openai-whisper",
                "engine_path": "python-package:openai-whisper",
                "precision": precision,
                "requested_batch": 1,
                "requested_height": 0,
                "requested_width": 0,
                "runtime_artifact_path": model_cache_path,
                "result_json_path": result_json_text,
            },
        },
        "preset_snapshot": {
            "name": "whisper/jetson_speech_smoke",
            "backend": "openai-whisper",
            "target": "jetson",
            "build_options": {
                "precision": precision,
                "model": model["name"],
                "audio_sample_rate_hz": audio["sample_rate_hz"],
                "measurement": "local_whisper_transcribe",
            },
            "metadata": {"validation_handoff": "inferedgelab", "source": "jetson-orin-nano-internal-lab"},
        },
        "export": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "source_whisper_smoke_json": source_text,
            "repo_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "repo_status": run_command(["git", "status", "--short", "--branch"]),
        },
    }
    return metadata_json, result_json


def build_inferedge_llm_export(llm_smoke_path: Path, output_dir: Path, repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build InferEdge-compatible metadata/result pair for local LLM text-generation evidence."""

    smoke = read_json(llm_smoke_path)
    metadata = smoke["metadata"]
    evidence = smoke["result"]
    if evidence.get("success") is not True or evidence.get("status") != "succeeded":
        raise ValueError(
            "LLM text-generation smoke must be successful before InferEdge export: "
            f"status={evidence.get('status')!r}, success={evidence.get('success')!r}"
        )

    model = evidence["model"]
    runtime = evidence["runtime"]
    latency = evidence["latency_ms"]
    generation = evidence["generation"]
    interpretation = evidence.get("interpretation", {})
    timestamp = now_iso()
    model_id = model["id"]
    model_alias = model["alias"]
    device = runtime["device"]
    precision = runtime["precision"]
    backend = evidence["framework"]
    source_text = _relative_or_original(str(llm_smoke_path), repo_root)
    result_json_text = _relative_or_original(str(output_dir / "result.json"), repo_root)
    tegrastats_text = metadata.get("tegrastats_log", "")
    tegrastats_summary = summarize_tegrastats(_path_from_repo(tegrastats_text, repo_root)) if tegrastats_text else {"status": "not_provided", "sample_count": 0}
    generated_token_count = generation.get("generated_token_count", 0)
    mean_seconds = latency["mean_ms"] / 1000.0 if latency.get("mean_ms") else 0.0
    generated_tokens_per_second = round(generated_token_count / mean_seconds, 4) if mean_seconds else None
    compare_model_name = model_id.replace("/", "_")
    compare_key = f"{compare_model_name}__text_generation__{device}__{precision}"
    backend_key = f"{backend}_{device}__jetson"
    engine_path = "python-package:transformers"
    power_mode = metadata.get("power_mode", {}).get("stdout", "unknown").replace("\n", "; ") or "unknown"

    result_json = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "compare_key": compare_key,
        "backend_key": backend_key,
        "runtime_role": "text-generation-result",
        "manifest_path": "",
        "manifest_applied": False,
        "model_name": model_id,
        "model_path": f"huggingface:{model_id}",
        "engine_name": "transformers",
        "engine_backend": "transformers",
        "device_name": "jetson",
        "batch": 1,
        "height": 0,
        "width": 0,
        "warmup": runtime["warmup"],
        "runs": runtime["repeat"],
        "mean_ms": latency["mean_ms"],
        "p50_ms": latency["p50_ms"],
        "p95_ms": latency["p95_ms"],
        "p99_ms": latency["p99_ms"],
        "fps_value": generated_tokens_per_second,
        "success": True,
        "status": "success",
        "model": {
            "path": f"huggingface:{model_id}",
            "name": model_id,
            "alias": model_alias,
            "family": "causal_lm",
            "sha256": "",
        },
        "engine": {
            "name": "transformers",
            "backend": "transformers",
            "available": metadata["package"]["transformers"]["available"],
            "status_message": "Tiny local LLM text-generation smoke completed.",
            "path": engine_path,
            "version": metadata["package"]["transformers"].get("version", ""),
            "sha256": "",
        },
        "device": {"name": "jetson", "hostname": metadata.get("hostname", "jetson-orin-nano")},
        "precision": precision,
        "run_config": {
            "batch": 1,
            "height": 0,
            "width": 0,
            "warmup": runtime["warmup"],
            "runs": runtime["repeat"],
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "device": device,
            "prompt": evidence["prompt"],
            "max_new_tokens": runtime["max_new_tokens"],
            "download_allowed": runtime["download_allowed"],
            "conda_env": metadata.get("conda_env", ""),
            "tegrastats_log_path": tegrastats_text,
            "manifest_path": "",
            "manifest_applied": False,
            "source_llm_smoke_json": source_text,
        },
        "latency_ms": {
            "mean": latency["mean_ms"],
            "min": latency["min_ms"],
            "max": latency["max_ms"],
            "std": None,
            "p50": latency["p50_ms"],
            "p90": None,
            "p95": latency["p95_ms"],
            "p99": latency["p99_ms"],
            "samples": latency["samples_ms"],
        },
        "fps": generated_tokens_per_second,
        "benchmark": {"success": True, "status": "success", "message": "LLM text-generation smoke exported to InferEdge-compatible result"},
        "timestamp": timestamp,
        "system": {
            "os": platform.system().lower(),
            "machine": platform.machine(),
            "jetson": {
                "power_mode": power_mode,
                "jetson_clocks": "unknown",
                "tegrastats_log_path": tegrastats_text,
            },
        },
        "jetson_evidence": {
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_summary": tegrastats_summary,
        },
        "model_metadata": {
            "inputs": [{"name": "prompt", "element_type": "utf8_text", "shape": [1], "prompt_token_count": generation["prompt_token_count"]}],
            "outputs": [{"name": "generated_text", "element_type": "utf8_text", "shape": [1], "generated_token_count": generated_token_count}],
        },
        "comparison": {
            "source_json": source_text,
            "comparison_name": "llm_text_generation_smoke",
            "verdict": "text_generation_smoke_not_quality_benchmark",
            "comparability": {
                "same_model_hash": False,
                "same_input_shape": True,
                "same_precision": True,
                "same_backend": True,
                "note": "tiny-gpt2 smoke validates local text-generation plumbing only; it is not a text quality benchmark or deployment approval",
            },
            "ratios": {"generated_tokens_per_second": generated_tokens_per_second},
        },
        "text_generation": {
            "prompt": evidence["prompt"],
            "generated_text": generation["text"],
            "prompt_token_count": generation["prompt_token_count"],
            "generated_token_count": generated_token_count,
            "max_new_tokens": runtime["max_new_tokens"],
            "download_allowed": runtime["download_allowed"],
            "quality_claim": bool(interpretation.get("quality_claim", False)),
            "deployment_ready_claim": bool(interpretation.get("deployment_ready_claim", False)),
        },
        "extra": {
            "runtime": "jetson-orin-nano-internal-lab",
            "json_export": "enabled",
            "output_mode": "explicit",
            "latest_path": result_json_text,
            "manifest_recorded": False,
            "manifest_precision": precision,
            "manifest_format": "transformers",
            "input_mode": "text_prompt",
            "input_path": "",
            "input_preprocess": "tokenizer_from_transformers",
            "power_mode": power_mode,
            "jetson_clocks": "unknown",
            "tegrastats_log_path": tegrastats_text,
            "tegrastats_status": tegrastats_summary.get("status", "unknown"),
            "compare_ready": True,
            "text_generation_ready": True,
            "compare_key": compare_key,
            "backend_key": backend_key,
            "compare_model_source": "huggingface_model_id",
            "compare_model_name": model_id,
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "evidence_kind": "llm_text_generation_smoke",
            "quality_claim": False,
            "deployment_ready_claim": False,
        },
    }

    metadata_json = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "source_model": {"format": "huggingface-model-id", "path": model_id, "sha256": ""},
        "artifacts": [
            {"role": "runtime_result", "format": "json", "path": result_json_text, "sha256": "__FILLED_AFTER_WRITE__"},
            {"role": "llm_smoke_result", "format": "json", "path": source_text, "sha256": sha256_file(llm_smoke_path)},
            {"role": "tegrastats_log", "format": "log", "path": tegrastats_text, "sha256": _sha256_if_exists(tegrastats_text, repo_root)},
        ],
        "build": {
            "build_id": f"llm-text-generation-{timestamp.replace(':', '').replace('-', '')}",
            "backend": "transformers",
            "target": "jetson",
            "preset_name": "llm/jetson_tiny_gpt2_smoke",
            "timestamp": timestamp,
        },
        "handoff": {"consumer": "InferEdgeLab", "ready": True},
        "lab_compat": {
            "profile_ready": True,
            "runtime": {
                "device": "jetson",
                "engine": "transformers",
                "engine_path": engine_path,
                "precision": precision,
                "requested_batch": 1,
                "requested_height": 0,
                "requested_width": 0,
                "runtime_artifact_path": f"huggingface:{model_id}",
                "result_json_path": result_json_text,
            },
        },
        "preset_snapshot": {
            "name": "llm/jetson_tiny_gpt2_smoke",
            "backend": "transformers",
            "target": "jetson",
            "build_options": {
                "precision": precision,
                "model": model_id,
                "device": device,
                "max_new_tokens": runtime["max_new_tokens"],
                "measurement": "local_transformers_generate",
            },
            "metadata": {"validation_handoff": "inferedgelab", "source": "jetson-orin-nano-internal-lab"},
        },
        "export": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "source_llm_smoke_json": source_text,
            "source_smoke_commit": metadata.get("git_commit", {}),
            "source_smoke_status": metadata.get("git_status", {}),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "export_workspace_status": run_command(["git", "status", "--short", "--branch"]),
            "artifact_commit_note": (
                "The commit containing this generated metadata is the git commit that tracks this file; "
                "it is intentionally not embedded to avoid self-referential commit hashes."
            ),
        },
    }
    return metadata_json, result_json


def validate_inferedge_metadata(payload: dict[str, Any]) -> None:
    required = ["schema_version", "source_model", "artifacts", "build", "handoff", "lab_compat"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"metadata missing keys: {missing}")
    if payload["schema_version"] != METADATA_SCHEMA_VERSION:
        raise ValueError("metadata schema_version mismatch")
    if not payload["handoff"].get("ready"):
        raise ValueError("metadata handoff.ready must be true")
    if not payload["lab_compat"].get("profile_ready"):
        raise ValueError("metadata lab_compat.profile_ready must be true")


def validate_inferedge_result(payload: dict[str, Any]) -> None:
    required = [
        "schema_version", "compare_key", "backend_key", "runtime_role", "model_name", "engine_backend",
        "device_name", "batch", "height", "width", "mean_ms", "p50_ms", "p95_ms", "p99_ms",
        "success", "status", "latency_ms", "jetson_evidence", "extra", "comparison",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"result missing keys: {missing}")
    if payload["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ValueError("result schema_version mismatch")
    if payload["status"] != "success" or payload["success"] is not True:
        raise ValueError("result must be successful")
    if payload["extra"].get("compare_ready") is not True:
        raise ValueError("result extra.compare_ready must be true")
    runtime_role = payload["runtime_role"]
    verdict = payload["comparison"]["verdict"]
    if runtime_role == "runtime-result" and verdict != "runtime_comparison_not_direct_regression":
        raise ValueError("comparison verdict must preserve runtime-comparison semantics")
    if runtime_role == "serving-result":
        if verdict != "serving_layer_evidence_not_direct_regression":
            raise ValueError("serving result must preserve serving-layer evidence semantics")
        if "serving" not in payload:
            raise ValueError("serving result missing serving details")
        if payload["extra"].get("serving_ready") is not True:
            raise ValueError("serving result extra.serving_ready must be true")
    if runtime_role == "audio-transcription-result":
        if verdict != "audio_transcription_smoke_not_accuracy_benchmark":
            raise ValueError("audio transcription result must preserve smoke-test semantics")
        if "audio" not in payload or "transcription" not in payload:
            raise ValueError("audio transcription result missing audio/transcription details")
        if payload["extra"].get("transcription_ready") is not True:
            raise ValueError("audio transcription result extra.transcription_ready must be true")
    if runtime_role == "text-generation-result":
        if verdict != "text_generation_smoke_not_quality_benchmark":
            raise ValueError("text generation result must preserve smoke-test semantics")
        if "text_generation" not in payload:
            raise ValueError("text generation result missing text_generation details")
        if payload["extra"].get("text_generation_ready") is not True:
            raise ValueError("text generation result extra.text_generation_ready must be true")
        if payload["extra"].get("quality_claim") is not False or payload["extra"].get("deployment_ready_claim") is not False:
            raise ValueError("text generation result must not claim quality or deployment readiness")
    if runtime_role not in {"runtime-result", "serving-result", "audio-transcription-result", "text-generation-result"}:
        raise ValueError(f"unsupported runtime_role: {runtime_role}")
