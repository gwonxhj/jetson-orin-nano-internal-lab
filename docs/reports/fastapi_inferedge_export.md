# FastAPI InferEdge Serving Export Report

> FastAPI localhost serving smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/resnet18_fastapi_serving_20260516_001440/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/resnet18_fastapi_serving_20260516_001440/result.json` | Lab-compatible serving result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `serving-result` |
| compare key | `resnet18__fastapi__b1__h224w224__fp32` |
| backend key | `fastapi_pytorch_cuda__jetson` |
| handoff ready | True |
| serving ready | True |
| verdict | `serving_layer_evidence_not_direct_regression` |

## Serving Summary

| Layer | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 31.0608 | 32.34 | 35.8785 |
| Server inference | 19.207 | 19.8549 | 20.1371 |

## Endpoint

| Field | Value |
|---|---|
| Framework | `fastapi` |
| ASGI | `uvicorn` |
| Endpoint | `/v1/infer/resnet18/synthetic` |
| Metrics endpoint | `/metrics` |
| Input shape | `[1, 3, 224, 224]` |
| Precision | `fp32` |

## Notes

- This is localhost serving-layer evidence, not a deployment approval.
- Client roundtrip latency includes local HTTP serialization and FastAPI routing overhead.
- Server inference latency is the PyTorch model call measured inside the FastAPI handler.
- `/metrics` snapshots are preserved as localhost smoke observability, not production monitoring evidence.
