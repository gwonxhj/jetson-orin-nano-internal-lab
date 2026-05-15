"""FastAPI inference server for Jetson local smoke evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any
import wave

import torch
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from torchvision.models import resnet18


MODEL_SEED = 42
DEFAULT_DEVICE = os.environ.get("JETSON_LAB_SERVER_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
DEFAULT_WHISPER_MODEL = os.environ.get("JETSON_LAB_WHISPER_MODEL", "tiny")
DEFAULT_WHISPER_AUDIO = "examples/audio/license_clear_whisper_smoke.wav"


class SyntheticInferenceRequest(BaseModel):
    batch_size: int = Field(default=1, ge=1, le=8)
    height: int = Field(default=224, ge=32, le=512)
    width: int = Field(default=224, ge=32, le=512)
    seed: int = Field(default=42, ge=0)


class WhisperSpeechRequest(BaseModel):
    audio_path: str = Field(default=DEFAULT_WHISPER_AUDIO)
    language: str = Field(default="en")
    expected_text: str = Field(default="hello world")


def state_dict_sha256(model: torch.nn.Module) -> str:
    canonical = {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
    buffer = io.BytesIO()
    torch.save(canonical, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def parameter_count(model: torch.nn.Module) -> int:
    return sum(param.numel() for param in model.parameters())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audio_metadata(path: Path, display_path: str | None = None) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        return {
            "path": display_path or str(path),
            "sha256": sha256_file(path),
            "format": "wav",
            "channels": handle.getnchannels(),
            "sample_width_bytes": handle.getsampwidth(),
            "sample_rate_hz": sample_rate,
            "frames": frames,
            "duration_s": round(frames / sample_rate, 4) if sample_rate else 0.0,
        }


class ModelBundle:
    def __init__(self, device_name: str) -> None:
        if device_name == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("requested CUDA server device but torch.cuda.is_available() is False")
        torch.manual_seed(MODEL_SEED)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(MODEL_SEED)
        self.device = torch.device(device_name)
        self.model = resnet18(weights=None).eval().to(self.device)
        self.model_hash = state_dict_sha256(self.model)
        self.parameter_count = parameter_count(self.model)

    def synthetic_input(self, request: SyntheticInferenceRequest) -> torch.Tensor:
        generator_device = self.device.type if self.device.type == "cuda" else "cpu"
        generator = torch.Generator(device=generator_device)
        generator.manual_seed(request.seed)
        return torch.rand(
            [request.batch_size, 3, request.height, request.width],
            dtype=torch.float32,
            device=self.device,
            generator=generator,
        )

    def infer(self, request: SyntheticInferenceRequest) -> dict[str, Any]:
        inputs = self.synthetic_input(request)
        with torch.inference_mode():
            start = time.perf_counter()
            output = self.model(inputs)
            if self.device.type == "cuda":
                torch.cuda.synchronize()
            inference_ms = (time.perf_counter() - start) * 1000.0
        output_cpu = output.detach().cpu()
        top_values, top_indices = torch.topk(output_cpu[0], k=min(5, output_cpu.shape[-1]))
        return {
            "inference_ms": round(inference_ms, 4),
            "output_shape": list(output_cpu.shape),
            "top5_indices": [int(v) for v in top_indices.tolist()],
            "top5_values": [round(float(v), 6) for v in top_values.tolist()],
        }


class WhisperBundle:
    def __init__(self, device_name: str, model_name: str) -> None:
        if importlib.util.find_spec("whisper") is None:
            raise RuntimeError("openai-whisper package is unavailable in this environment")
        import whisper

        if device_name == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("requested CUDA Whisper device but torch.cuda.is_available() is False")
        self.device_name = device_name
        self.model_name = model_name
        self.cache_path = Path.home() / ".cache" / "whisper" / f"{model_name}.pt"
        self.package_version = getattr(whisper, "__version__", "unknown")
        self.model = whisper.load_model(model_name, device=device_name, download_root=str(self.cache_path.parent))

    def transcribe(self, audio_path: Path, language: str) -> dict[str, Any]:
        start = time.perf_counter()
        result = self.model.transcribe(str(audio_path), language=language, fp16=(self.device_name == "cuda"))
        if self.device_name == "cuda" and torch.cuda.is_available():
            torch.cuda.synchronize()
        inference_ms = (time.perf_counter() - start) * 1000.0
        text = str(result.get("text", "")).strip()
        return {
            "inference_ms": round(inference_ms, 4),
            "text": text,
            "language": result.get("language", language),
            "segments": [
                {
                    "start": round(float(segment.get("start", 0.0)), 3),
                    "end": round(float(segment.get("end", 0.0)), 3),
                    "text": str(segment.get("text", "")).strip(),
                }
                for segment in result.get("segments", [])
            ],
        }


@lru_cache(maxsize=1)
def get_bundle() -> ModelBundle:
    return ModelBundle(DEFAULT_DEVICE)


@lru_cache(maxsize=1)
def get_whisper_bundle() -> WhisperBundle:
    return WhisperBundle(DEFAULT_DEVICE, DEFAULT_WHISPER_MODEL)


def whisper_status() -> dict[str, Any]:
    cache_path = Path.home() / ".cache" / "whisper" / f"{DEFAULT_WHISPER_MODEL}.pt"
    return {
        "id": f"whisper-{DEFAULT_WHISPER_MODEL}",
        "architecture": "whisper",
        "backend": "openai-whisper",
        "package_available": importlib.util.find_spec("whisper") is not None,
        "model_cache_present": cache_path.exists(),
        "device": DEFAULT_DEVICE,
        "precision": "fp32_or_fp16_by_device",
    }


class MetricsStore:
    def __init__(self) -> None:
        self.started_at = time.time()
        self._lock = Lock()
        self.total_requests = 0
        self.by_path: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_ms": 0.0, "max_ms": 0.0, "last_status_code": None, "methods": set()}
        )

    def record(self, method: str, path: str, status_code: int, elapsed_ms: float) -> None:
        with self._lock:
            self.total_requests += 1
            item = self.by_path[path]
            item["count"] += 1
            item["total_ms"] += elapsed_ms
            item["max_ms"] = max(float(item["max_ms"]), elapsed_ms)
            item["last_status_code"] = status_code
            item["methods"].add(method)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            by_path = {}
            for path, item in sorted(self.by_path.items()):
                count = int(item["count"])
                by_path[path] = {
                    "count": count,
                    "methods": sorted(item["methods"]),
                    "mean_ms": round(float(item["total_ms"]) / count, 4) if count else 0.0,
                    "max_ms": round(float(item["max_ms"]), 4),
                    "last_status_code": item["last_status_code"],
                }
            total_requests = self.total_requests

        process = {"pid": os.getpid()}
        try:
            import resource

            process["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 3)
        except Exception as exc:
            process["max_rss_unavailable"] = repr(exc)

        cuda: dict[str, Any] = {"available": torch.cuda.is_available()}
        if torch.cuda.is_available():
            cuda.update(
                {
                    "device_count": torch.cuda.device_count(),
                    "current_device": torch.cuda.current_device(),
                    "memory_allocated_mb": round(torch.cuda.memory_allocated() / (1024 * 1024), 3),
                    "memory_reserved_mb": round(torch.cuda.memory_reserved() / (1024 * 1024), 3),
                }
            )

        return {
            "schema_version": "fastapi-metrics-v1",
            "status": "ok",
            "uptime_s": round(time.time() - self.started_at, 3),
            "process": process,
            "requests": {"total": total_requests, "by_path": by_path},
            "runtime": {
                "device_default": DEFAULT_DEVICE,
                "resnet18_loaded": get_bundle.cache_info().currsize > 0,
                "whisper_loaded": get_whisper_bundle.cache_info().currsize > 0,
                "torch": {"version": torch.__version__, "cuda": cuda},
            },
            "interpretation": {
                "deployment_ready_claim": False,
                "notes": "Local in-process counters for localhost smoke evidence; not a production observability stack.",
            },
        }


app = FastAPI(title="Jetson Orin Nano Internal Lab Server", version="0.2.0")
app.state.metrics = MetricsStore()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        app.state.metrics.record(request.method, request.url.path, status_code, elapsed_ms)


@app.get("/health")
def health() -> dict[str, Any]:
    bundle = get_bundle()
    return {
        "status": "ok",
        "model": "resnet18",
        "device": bundle.device.type,
        "precision": "fp32",
        "model_hash": bundle.model_hash,
        "services": {
            "resnet18": {"status": "ok", "device": bundle.device.type, "precision": "fp32"},
            "whisper": whisper_status(),
        },
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    bundle = get_bundle()
    return {
        "models": [
            {
                "id": "resnet18-random-seed42",
                "architecture": "resnet18",
                "weights": "random_seeded_weights_no_pretrained_accuracy_claim",
                "parameter_count": bundle.parameter_count,
                "state_dict_sha256": bundle.model_hash,
                "device": bundle.device.type,
                "precision": "fp32",
            },
            whisper_status(),
        ]
    }


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return app.state.metrics.snapshot()


@app.post("/v1/infer/resnet18/synthetic")
def infer_resnet18_synthetic(request: SyntheticInferenceRequest) -> dict[str, Any]:
    bundle = get_bundle()
    result = bundle.infer(request)
    return {
        "task": "image_classification_smoke",
        "framework": "pytorch",
        "server": "fastapi",
        "backend": bundle.device.type,
        "precision": "fp32",
        "model": {
            "architecture": "resnet18",
            "weights": "random_seeded_weights_no_pretrained_accuracy_claim",
            "state_dict_sha256": bundle.model_hash,
        },
        "input": {
            "source": "synthetic_random_tensor",
            "shape": [request.batch_size, 3, request.height, request.width],
            "dtype": "float32",
            "seed": request.seed,
        },
        "result": result,
    }


@app.post("/v1/infer/whisper/speech")
def infer_whisper_speech(request: WhisperSpeechRequest) -> dict[str, Any]:
    audio_path = Path(request.audio_path)
    if audio_path.is_absolute():
        raise HTTPException(status_code=400, detail="audio_path must be repo-relative")
    if ".." in audio_path.parts:
        raise HTTPException(status_code=400, detail="audio_path must not traverse parent directories")
    audio_path = Path.cwd() / audio_path
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"audio file not found: {request.audio_path}")
    try:
        bundle = get_whisper_bundle()
    except Exception as exc:
        return {
            "task": "audio_transcription_serving_smoke",
            "framework": "whisper",
            "server": "fastapi",
            "backend": DEFAULT_DEVICE,
            "precision": "fp32_or_fp16_by_device",
            "status": "dependency_missing",
            "success": False,
            "failure_reason": repr(exc),
            "model": whisper_status(),
            "input": audio_metadata(audio_path, request.audio_path),
            "result": {"inference_ms": None, "text": "", "language": request.language, "segments": []},
            "interpretation": {
                "accuracy_claim": False,
                "deployment_ready_claim": False,
                "external_sensor_dependency": False,
            },
        }

    result = bundle.transcribe(audio_path, request.language)
    audio = audio_metadata(audio_path, request.audio_path)
    return {
        "task": "audio_transcription_serving_smoke",
        "framework": "whisper",
        "server": "fastapi",
        "backend": bundle.device_name,
        "precision": "fp32_or_fp16_by_device",
        "status": "succeeded",
        "success": True,
        "model": {
            "id": f"whisper-{bundle.model_name}",
            "architecture": "whisper",
            "backend": "openai-whisper",
            "package_version": bundle.package_version,
            "cache_path": "[home]/.cache/whisper/" + f"{bundle.model_name}.pt",
            "cache_present": bundle.cache_path.exists(),
            "device": bundle.device_name,
        },
        "input": {
            **audio,
            "source": "generated_license_clear_ffmpeg_flite_text_to_speech",
            "expected_text": request.expected_text,
        },
        "result": result,
        "interpretation": {
            "accuracy_claim": False,
            "deployment_ready_claim": False,
            "external_sensor_dependency": False,
            "notes": "License-clear generated speech input validates a localhost audio serving path; it is not a broad recognition accuracy benchmark.",
        },
    }
