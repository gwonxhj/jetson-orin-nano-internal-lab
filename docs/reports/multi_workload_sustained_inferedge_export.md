# Multi-Workload InferEdge Export Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.
> 이 export는 runtime interaction / reliability signal handoff이며 production stress test나 deployment-ready proof가 아닙니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/multi_workload_sustained_20260518_002910/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/multi_workload_sustained_20260518_002910/result.json` | Lab-compatible multi-workload runtime result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `multi-workload-runtime-result` |
| compare key | `multi_workload__yolo_whisper_fastapi__1800s__jetson` |
| backend key | `mixed_yolo_fastapi_whisper__jetson` |
| handoff ready | True |
| runtime reliability ready | True |
| verdict | `multi_workload_runtime_interaction_evidence_not_production_stress_test` |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 34324 | 34324 | 0 | 54.2977 | 68.0591 | 785.0608 |
| fastapi_whisper | 5 | 5 | 0 | 1313.5877 | 3521.1574 | 4243.5182 |
| yolo_detection | 1606 | 1606 | 0 | 117.7534 | 144.4643 | 1341.9493 |

## Interaction Window

- Whisper window: 300.0338s -> 1506.832s
- FastAPI during/after p95 ratio: `0.9824`
- YOLO during/after p95 ratio: `1.0025`
- Total success events/sec: `19.9629`

## Evidence Paths

- Source result: `results/runtime_compare/multi_workload_sustained_20260518_002910.json`
- Server log: `artifacts/system/fastapi_multi_workload_server_20260518_002910.log`
- Tegrastats log: `artifacts/system/tegrastats_multi_workload_20260518_002910.log`

## Notes

- This is multi-workload runtime interaction evidence, not a direct single-model regression comparison.
- Latency spikes and contention windows are preserved as runtime reliability signals.
- The scenario uses local file/audio/synthetic inputs and does not rely on external cameras, sensors, microphones, motors, or robot hardware.
- The top-level latency summary uses FastAPI ResNet18 client request latency so the handoff remains comparable to serving behavior evidence; detailed YOLO/Whisper latency remains under `workload_interaction`.
