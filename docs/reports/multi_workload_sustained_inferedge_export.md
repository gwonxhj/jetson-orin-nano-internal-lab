# Multi-Workload InferEdge Export Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.
> 이 export는 runtime interaction / reliability signal handoff이며 production stress test나 deployment-ready proof가 아닙니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/multi_workload_sustained_20260517_213947/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/multi_workload_sustained_20260517_213947/result.json` | Lab-compatible multi-workload runtime result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `multi-workload-runtime-result` |
| compare key | `multi_workload__yolo_whisper_fastapi__30s__jetson` |
| backend key | `mixed_yolo_fastapi_whisper__jetson` |
| handoff ready | True |
| runtime reliability ready | True |
| verdict | `multi_workload_runtime_interaction_evidence_not_production_stress_test` |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 535 | 535 | 0 | 60.9927 | 86.832 | 771.9765 |
| fastapi_whisper | 1 | 1 | 0 | 3846.2144 | 3846.2144 | 3846.2144 |
| yolo_detection | 23 | 23 | 0 | 158.9743 | 142.8149 | 1323.5524 |

## Interaction Window

- Whisper window: 8.0095s -> 11.8557s
- FastAPI during/after p95 ratio: `2.1543`
- YOLO during/after p95 ratio: `0.8166`
- Total success events/sec: `18.6152`

## Evidence Paths

- Source result: `results/runtime_compare/multi_workload_sustained_20260517_213947.json`
- Server log: `artifacts/system/fastapi_multi_workload_server_20260517_213947.log`
- Tegrastats log: `artifacts/system/tegrastats_multi_workload_20260517_213947.log`

## Notes

- This is multi-workload runtime interaction evidence, not a direct single-model regression comparison.
- Latency spikes and contention windows are preserved as runtime reliability signals.
- The scenario uses local file/audio/synthetic inputs and does not rely on external cameras, sensors, microphones, motors, or robot hardware.
- The top-level latency summary uses FastAPI ResNet18 client request latency so the handoff remains comparable to serving behavior evidence; detailed YOLO/Whisper latency remains under `workload_interaction`.
