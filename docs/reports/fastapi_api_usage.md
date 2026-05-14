# FastAPI API Usage Report

> FastAPI ResNet18 localhost server의 `/health`, `/v1/models`, `/v1/infer/resnet18/synthetic` 호출 흐름과, 호출 결과가 어떤 evidence 산출물로 이어지는지 정리한 보고서입니다.
> Synthetic input과 random seeded weights를 사용하므로 accuracy evidence가 아니라 local serving path evidence입니다.

## Purpose

이 report는 GitHub 방문자가 FastAPI serving layer를 다음 순서로 재현하고 읽을 수 있게 하는 guide 역할을 합니다.

1. 서버가 올라왔는지 확인합니다.
2. 모델 id, device, precision, model hash를 확인합니다.
3. synthetic inference endpoint를 호출합니다.
4. client/server latency smoke를 실행합니다.
5. serving smoke를 InferEdge-compatible `metadata.json` / `result.json`으로 export합니다.

## Start Server

검증된 환경은 Jetson의 `yolo_env`입니다.

```bash
cd ~/jetson-orin-nano-internal-lab
source ~/miniconda3/etc/profile.d/conda.sh
conda activate yolo_env

JETSON_LAB_SERVER_DEVICE=cuda \
python3 -m uvicorn src.server.resnet18_app:app \
  --host 127.0.0.1 \
  --port 18080 \
  --log-level info
```

## Endpoint Flow

| Step | Endpoint | Method | Purpose | Evidence field |
|---|---|---|---|---|
| 1 | `/health` | GET | Server readiness, active device, precision, model hash | `result.server.health` |
| 2 | `/v1/models` | GET | Model id, architecture, seeded weight hash, parameter count | `result.model` |
| 3 | `/v1/infer/resnet18/synthetic` | POST | Synthetic ResNet18 inference through FastAPI/PyTorch | `result.output`, `serving.request` |

### 1. Health Check

```bash
curl -s http://127.0.0.1:18080/health | python3 -m json.tool
```

Expected shape:

```json
{
  "status": "ok",
  "model": "resnet18",
  "device": "cuda",
  "precision": "fp32",
  "model_hash": "9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245"
}
```

### 2. Model Registry

```bash
curl -s http://127.0.0.1:18080/v1/models | python3 -m json.tool
```

Expected fields:

| Field | Meaning |
|---|---|
| `id` | `resnet18-random-seed42` model identifier |
| `architecture` | `resnet18` |
| `weights` | Random seeded weights, no pretrained accuracy claim |
| `state_dict_sha256` | Canonical model hash shared with PyTorch smoke |
| `device` | Runtime device selected by `JETSON_LAB_SERVER_DEVICE` |
| `precision` | `fp32` |

### 3. Synthetic Inference

```bash
curl -s \
  -X POST http://127.0.0.1:18080/v1/infer/resnet18/synthetic \
  -H 'Content-Type: application/json' \
  -d '{"batch_size":1,"height":224,"width":224,"seed":42}' \
  | python3 -m json.tool
```

Request schema:

| Field | Default | Constraint | Meaning |
|---|---:|---|---|
| `batch_size` | 1 | 1 to 8 | Synthetic batch size |
| `height` | 224 | 32 to 512 | Input height |
| `width` | 224 | 32 to 512 | Input width |
| `seed` | 42 | >= 0 | Synthetic tensor seed |

Response evidence fields:

| Field | Meaning |
|---|---|
| `backend` | PyTorch backend device, usually `cuda` on Jetson |
| `precision` | `fp32` |
| `model.state_dict_sha256` | Same seeded ResNet18 model hash used across smoke evidence |
| `input.shape` | Synthetic input shape |
| `result.inference_ms` | Server-side model call latency measured inside FastAPI handler |
| `result.output_shape` | ResNet18 logits shape, `[1, 1000]` for batch 1 |
| `result.top5_indices`, `result.top5_values` | Smoke output preview, not accuracy evidence |

## Evidence Commands

`scripts/run_fastapi_server_smoke.sh` starts the server, captures `tegrastats`, runs warmup/repeat calls, and writes the serving smoke JSON/report.

```bash
bash scripts/run_fastapi_server_smoke.sh
```

Serving smoke output:

| Artifact | Path |
|---|---|
| Result JSON | `results/inference/fastapi_resnet18_server_20260514_142053.json` |
| Report | `docs/reports/fastapi_resnet18_server_smoke.md` |
| Server log | `artifacts/system/fastapi_resnet18_server_20260514_142053.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_resnet18_20260514_142053.log` |

`scripts/export_fastapi_serving_inferedge.sh` converts that serving smoke JSON into InferEdge-compatible handoff evidence.

```bash
bash scripts/export_fastapi_serving_inferedge.sh
```

InferEdge serving output:

| Artifact | Path |
|---|---|
| Metadata | `results/inferedge/resnet18_fastapi_serving_20260514_142053/metadata.json` |
| Result | `results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json` |
| Report | `docs/reports/fastapi_inferedge_export.md` |

## Current Recorded Result

| Layer | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 28.5178 | 29.5806 | 29.6584 |
| Server inference | 18.415 | 19.1253 | 19.2008 |

## Interpretation

- `/health` and `/v1/models` are reproducibility checks, not benchmark endpoints.
- `/v1/infer/resnet18/synthetic` uses synthetic tensors and random seeded weights, so it proves the local serving path, not model accuracy.
- Client roundtrip latency includes localhost HTTP serialization, FastAPI routing, request validation, synthetic tensor creation, inference, and response serialization.
- Server inference latency is measured inside the handler around the PyTorch model call.
- The InferEdge serving export uses client roundtrip latency as the top-level `latency_ms` and preserves server-side latency under `serving.latency_layers.server_inference_ms`.
- This serving evidence does not replace native TensorRT or ONNX Runtime provider evidence; it adds a local API layer evidence point.
