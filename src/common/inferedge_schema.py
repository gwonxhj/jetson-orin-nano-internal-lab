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
    if runtime_role not in {"runtime-result", "serving-result"}:
        raise ValueError(f"unsupported runtime_role: {runtime_role}")
