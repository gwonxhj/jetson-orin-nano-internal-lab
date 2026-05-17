# FastAPI API Usage Report

> FastAPI localhost server의 `/health`, `/v1/models`, `/metrics`, `/v1/infer/resnet18/synthetic`, `/v1/infer/whisper/speech` 호출 흐름과, 호출 결과가 어떤 evidence 산출물로 이어지는지 정리한 보고서입니다.
> ResNet18은 synthetic input과 random seeded weights를 사용하고, Whisper는 license-clear generated speech sample을 사용하므로 accuracy evidence가 아니라 local serving path evidence입니다.

## Purpose

이 report는 GitHub 방문자가 FastAPI serving layer를 다음 순서로 재현하고 읽을 수 있게 하는 guide 역할을 합니다.

1. 서버가 올라왔는지 확인합니다.
2. 모델 id, device, precision, model hash를 확인합니다.
3. `/metrics`로 localhost in-process counters와 runtime 상태를 확인합니다.
4. ResNet18 synthetic inference endpoint를 호출합니다.
5. Whisper speech transcription endpoint를 호출합니다.
6. client/server latency smoke를 실행합니다.
7. short localhost concurrency smoke를 실행합니다.
8. serving smoke를 InferEdge-compatible `metadata.json` / `result.json`으로 export합니다.

## Start Server

ResNet18 API smoke의 검증된 환경은 Jetson의 `yolo_env`입니다.

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

Whisper API smoke는 기존 `yolo_env`를 직접 변경하지 않고, 격리된 `whisper_env`에서 실행합니다.

```bash
cd ~/jetson-orin-nano-internal-lab
source ~/miniconda3/etc/profile.d/conda.sh
conda activate whisper_env

JETSON_LAB_SERVER_DEVICE=cuda \
JETSON_LAB_WHISPER_MODEL=tiny \
python3 -m uvicorn src.server.resnet18_app:app \
  --host 127.0.0.1 \
  --port 18081 \
  --log-level info
```

## Endpoint Flow

| Step | Endpoint | Method | Purpose | Evidence field |
|---|---|---|---|---|
| 1 | `/health` | GET | Server readiness, active device, ResNet18 hash, Whisper package/cache availability | `result.server.health` |
| 2 | `/v1/models` | GET | ResNet18 model hash and Whisper provider/cache status | `result.model` |
| 3 | `/metrics` | GET | Local request counters, process RSS, CUDA memory, model loaded state, in-flight/failed request counters, backlog proxy | `result.server.metrics`, `result.serving_observability` |
| 4 | `/v1/infer/resnet18/synthetic` | POST | Synthetic ResNet18 inference through FastAPI/PyTorch | `result.output`, `serving.request` |
| 5 | `/v1/infer/whisper/speech` | POST | License-clear generated speech transcription through FastAPI/Whisper | `result.transcription`, `result.input` |

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
  "model_hash": "9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245",
  "services": {
    "resnet18": {"status": "available"},
    "whisper": {"id": "whisper-tiny", "status": "available_or_dependency_missing"}
  }
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

Whisper rows include `id`, `architecture`, `backend`, `package_available`, `cache_present`, `device`, and `precision`.

### 3. Metrics Snapshot

```bash
curl -s http://127.0.0.1:18080/metrics | python3 -m json.tool
```

Expected fields:

| Field | Meaning |
|---|---|
| `schema_version` | `fastapi-metrics-v1` JSON evidence shape |
| `uptime_s` | In-process server uptime at call time |
| `requests.total` | Number of requests observed by this process |
| `requests.failed` | Number of HTTP status >= 400 responses observed by this process |
| `requests.status_codes` | HTTP status-code counts retained for smoke/report evidence |
| `requests.by_path` | Per-path count, failed count, status-code count, method list, mean/max handler wall time, latest status |
| `serving_observability.inflight_requests` | Current in-process request count at snapshot time |
| `serving_observability.max_inflight_requests` | Maximum in-process concurrent request count seen by this server process |
| `serving_observability.backlog_proxy` | Lightweight backlog/dropped-request proxy; not ASGI production queue depth |
| `runtime.resnet18_loaded` | Whether the cached ResNet18 bundle has been initialized |
| `runtime.whisper_loaded` | Whether the cached Whisper bundle has been initialized |
| `runtime.torch.cuda` | CUDA availability and memory counters from PyTorch when CUDA is available |

This endpoint is localhost smoke observability. It is not Prometheus, uptime, alerting, or production capacity evidence.

### 4. Synthetic Inference

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

### 5. Whisper Speech Transcription

```bash
curl -s \
  -X POST http://127.0.0.1:18081/v1/infer/whisper/speech \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"examples/audio/license_clear_whisper_smoke.wav","language":"en","expected_text":"hello world"}' \
  | python3 -m json.tool
```

Request schema:

| Field | Default | Constraint | Meaning |
|---|---|---|---|
| `audio_path` | `examples/audio/license_clear_whisper_smoke.wav` | repo-relative path, no `..` traversal | License-clear WAV sample to transcribe |
| `language` | `en` | Whisper language code | Language hint for `model.transcribe` |
| `expected_text` | `hello world` | smoke note only | Expected short phrase used for normalized smoke match |

Response evidence fields:

| Field | Meaning |
|---|---|
| `backend` | Whisper runtime device, `cuda` in the recorded `whisper_env` smoke |
| `precision` | `fp32_or_fp16_by_device`; openai-whisper uses fp16 on CUDA in this endpoint |
| `model.id` | `whisper-tiny` |
| `input.path`, `input.sha256` | Repo-relative audio path and content hash |
| `result.inference_ms` | Server-side transcription timing measured inside FastAPI handler |
| `result.text` | Transcribed text, currently `Hello world!` |
| `interpretation.accuracy_claim` | Always false for this short generated speech smoke |

## Evidence Commands

`scripts/run_fastapi_server_smoke.sh` starts the server, captures `tegrastats`, calls `/metrics` before/after warmup/repeat inference, and writes the serving smoke JSON/report.

```bash
bash scripts/run_fastapi_server_smoke.sh
```

Serving smoke output:

| Artifact | Path |
|---|---|
| Result JSON | `results/inference/fastapi_resnet18_server_20260516_001440.json` |
| Report | `docs/reports/fastapi_resnet18_server_smoke.md` |
| Server log | `artifacts/system/fastapi_resnet18_server_20260516_001440.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_resnet18_20260516_001440.log` |

`scripts/run_fastapi_whisper_smoke.sh` starts the same app in `whisper_env`, captures `tegrastats`, calls `/v1/infer/whisper/speech`, and writes audio serving smoke JSON/report.

```bash
conda activate whisper_env
bash scripts/run_fastapi_whisper_smoke.sh
```

Whisper serving smoke output:

| Artifact | Path |
|---|---|
| Result JSON | `results/inference/fastapi_whisper_speech_server_20260514_202459.json` |
| Report | `docs/reports/fastapi_whisper_speech_server_smoke.md` |
| Server log | `artifacts/system/fastapi_whisper_server_20260514_202459.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_whisper_20260514_202459.log` |

`scripts/run_fastapi_concurrency_smoke.sh` starts the ResNet18 API server and issues short localhost concurrent requests grouped by concurrency level.

```bash
bash scripts/run_fastapi_concurrency_smoke.sh
```

Concurrency smoke output:

| Artifact | Path |
|---|---|
| Result JSON | `results/inference/fastapi_resnet18_concurrency_20260514_233246.json` |
| Report | `docs/reports/fastapi_concurrency_smoke.md` |
| Server log | `artifacts/system/fastapi_concurrency_server_*.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_concurrency_*.log` |

`scripts/export_fastapi_serving_inferedge.sh` converts that serving smoke JSON into InferEdge-compatible handoff evidence.

```bash
bash scripts/export_fastapi_serving_inferedge.sh
```

InferEdge serving output:

| Artifact | Path |
|---|---|
| Metadata | `results/inferedge/resnet18_fastapi_serving_20260516_001440/metadata.json` |
| Result | `results/inferedge/resnet18_fastapi_serving_20260516_001440/result.json` |
| Report | `docs/reports/fastapi_inferedge_export.md` |

`scripts/export_fastapi_whisper_serving_inferedge.sh` converts the Whisper serving smoke JSON into a matching InferEdge-compatible serving handoff.

```bash
bash scripts/export_fastapi_whisper_serving_inferedge.sh
```

InferEdge Whisper serving output:

| Artifact | Path |
|---|---|
| Metadata | `results/inferedge/fastapi_whisper_serving_20260514_202459/metadata.json` |
| Result | `results/inferedge/fastapi_whisper_serving_20260514_202459/result.json` |
| Report | `docs/reports/fastapi_whisper_inferedge_export.md` |

## Current Recorded Result

| Endpoint | Layer | Mean ms | P95 ms | P99 ms |
|---|---|---:|---:|---:|
| `/v1/infer/resnet18/synthetic` | Client roundtrip | 28.5178 | 29.5806 | 29.6584 |
| `/v1/infer/resnet18/synthetic` | Server inference | 18.415 | 19.1253 | 19.2008 |
| `/v1/infer/whisper/speech` | Client roundtrip | 3276.5571 | 3276.5571 | 3276.5571 |
| `/v1/infer/whisper/speech` | Server transcription | 1802.9543 | 1802.9543 | 1802.9543 |

## Interpretation

- `/health` and `/v1/models` are reproducibility checks, not benchmark endpoints.
- `/v1/infer/resnet18/synthetic` uses synthetic tensors and random seeded weights, so it proves the local serving path, not model accuracy.
- `/v1/infer/whisper/speech` uses a short generated WAV sample, so it proves the local audio serving path and transcription plumbing, not broad speech recognition accuracy.
- FastAPI concurrency smoke is a short localhost path check; it is not a production load test or capacity plan.
- Client roundtrip latency includes localhost HTTP serialization, FastAPI routing, request validation, synthetic tensor creation, inference, and response serialization.
- Server inference/transcription latency is measured inside the handler around the PyTorch model call or Whisper `model.transcribe`.
- The InferEdge serving export uses client roundtrip latency as the top-level `latency_ms` and preserves server-side latency under `serving.latency_layers.server_inference_ms`.
- The FastAPI Whisper serving export also uses client roundtrip latency as top-level `latency_ms`, while preserving transcription timing under `serving.latency_layers.server_transcription_ms`.
- This serving evidence does not replace native TensorRT or ONNX Runtime provider evidence; it adds a local API layer evidence point.
