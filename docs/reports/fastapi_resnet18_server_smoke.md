# FastAPI ResNet18 Server Smoke Report

> ResNet18 PyTorch CUDA path를 localhost FastAPI serving layer로 감싼 smoke evidence입니다.
> Synthetic input과 random seeded weights를 사용하므로 accuracy evidence가 아니라 local serving path evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T14:21:02+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18080` |
| Endpoint | `/v1/infer/resnet18/synthetic` |
| Server log | `artifacts/system/fastapi_resnet18_server_20260514_142053.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_resnet18_20260514_142053.log` |

## Model / Request

| Field | Value |
|---|---|
| Model | resnet18 |
| Model hash | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` |
| Backend | cuda |
| Precision | fp32 |
| Input shape | [1, 3, 224, 224] |
| Warmup / repeat | 5 / 30 |

## Latency

| Metric | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 28.5178 | 29.5806 | 29.6584 |
| Server inference | 18.415 | 19.1253 | 19.2008 |

## Interpretation

- Client roundtrip includes local HTTP serialization and FastAPI routing overhead.
- Server inference is measured inside the FastAPI handler around the PyTorch model call.
- This does not replace TensorRT/ORT provider evidence; it adds a local serving layer evidence point.
