# Multi-Workload Sustained Runtime Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.
> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-18T01:41:33+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18086` |
| Duration | 300.08 s |
| Server log | `artifacts/system/fastapi_multi_workload_degradation_server_20260518_013625.log` |
| Tegrastats log | `artifacts/system/tegrastats_multi_workload_degradation_20260518_013625.log` |
| Mock workloads | False |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 15472 | 15472 | 0 | 144.1454 | 173.0672 | 883.8447 |
| fastapi_whisper | 3 | 3 | 0 | 4850.8652 | 8787.4625 | 9437.4952 |
| yolo_detection | 751 | 751 | 0 | 142.3628 | 173.2865 | 1690.4935 |

## Interaction Window

- Whisper burst window: 60.0481s -> 194.7179s

### YOLO

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 136 | 153.8967 | 173.0657 | 1690.4935 |
| During Whisper | 347 | 138.2523 | 171.9909 | 186.5689 |
| After Whisper | 268 | 141.8321 | 174.7809 | 189.2701 |

### FastAPI ResNet18

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 3114 | 142.9639 | 170.3869 | 825.2628 |
| During Whisper | 6874 | 145.8961 | 178.4501 | 883.8447 |
| After Whisper | 5484 | 142.6218 | 169.5255 | 506.1573 |

## Boundary

- This is multi-workload runtime interaction evidence, not a production stress test.
- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.
- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.
- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.
