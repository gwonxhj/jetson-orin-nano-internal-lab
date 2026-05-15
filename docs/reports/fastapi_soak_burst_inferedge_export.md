# FastAPI Soak/Burst InferEdge Export Report

> FastAPI ResNet18 localhost soak/burst evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/fastapi_resnet18_soak_burst_20260515_222841/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/fastapi_resnet18_soak_burst_20260515_222841/result.json` | Lab-compatible serving result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `serving-result` |
| compare key | `resnet18__fastapi_soak_burst__b1__h224w224__fp32` |
| backend key | `fastapi_pytorch_cuda_soak_burst__jetson` |
| handoff ready | True |
| serving ready | True |
| verdict | `serving_layer_evidence_not_direct_regression` |

## Soak Summary

| Metric | Value |
|---|---:|
| Soak duration s | 60.0 |
| Soak concurrency | 2 |
| Requests | 2776 |
| Success | 2776 |
| Errors | 0 |
| Throughput rps | 46.2431 |

## Latency

| Layer | Mean ms | P95 ms | P99 ms |
|---|---:|---:|---:|
| Client roundtrip | 42.0217 | 43.7574 | 46.3252 |
| Server inference | 26.2387 | 26.8632 | 27.5486 |

## Burst Summary

| Concurrency | Requests | Success | Errors | Throughput rps | Client p95 ms | Server p95 ms |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 16 | 0 | 37.0759 | 26.8395 | 17.596 |
| 2 | 16 | 16 | 0 | 46.8496 | 44.6023 | 27.6746 |
| 4 | 16 | 16 | 0 | 55.9909 | 134.1225 | 113.6965 |
| 8 | 16 | 16 | 0 | 53.6367 | 234.0573 | 193.3753 |

## Notes

- This is localhost serving-layer evidence, not deployment approval.
- The export keeps soak and burst sections under `serving` while using soak client roundtrip latency as the top-level serving summary.
- Client roundtrip and server handler inference remain separate so API overhead is not collapsed into model latency.
- This evidence does not claim capacity planning or production load-test coverage.
