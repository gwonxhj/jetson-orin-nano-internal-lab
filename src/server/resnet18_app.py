"""FastAPI ResNet18 synthetic inference server for Jetson local smoke evidence."""

from __future__ import annotations

import hashlib
import io
import os
import time
from functools import lru_cache
from typing import Any

import torch
from fastapi import FastAPI
from pydantic import BaseModel, Field
from torchvision.models import resnet18


MODEL_SEED = 42
DEFAULT_DEVICE = os.environ.get("JETSON_LAB_SERVER_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")


class SyntheticInferenceRequest(BaseModel):
    batch_size: int = Field(default=1, ge=1, le=8)
    height: int = Field(default=224, ge=32, le=512)
    width: int = Field(default=224, ge=32, le=512)
    seed: int = Field(default=42, ge=0)


def state_dict_sha256(model: torch.nn.Module) -> str:
    canonical = {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()}
    buffer = io.BytesIO()
    torch.save(canonical, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def parameter_count(model: torch.nn.Module) -> int:
    return sum(param.numel() for param in model.parameters())


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


@lru_cache(maxsize=1)
def get_bundle() -> ModelBundle:
    return ModelBundle(DEFAULT_DEVICE)


app = FastAPI(title="Jetson Orin Nano Internal Lab ResNet18 Server", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    bundle = get_bundle()
    return {
        "status": "ok",
        "model": "resnet18",
        "device": bundle.device.type,
        "precision": "fp32",
        "model_hash": bundle.model_hash,
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
            }
        ]
    }


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
