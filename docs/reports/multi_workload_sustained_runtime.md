# Multi-Workload Sustained Runtime Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.
> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-17T21:40:24+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18085` |
| Duration | 30.0292 s |
| Server log | `artifacts/system/fastapi_multi_workload_server_20260517_213947.log` |
| Tegrastats log | `artifacts/system/tegrastats_multi_workload_20260517_213947.log` |
| Mock workloads | False |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 535 | 535 | 0 | 60.9927 | 86.832 | 771.9765 |
| fastapi_whisper | 1 | 1 | 0 | 3846.2144 | 3846.2144 | 3846.2144 |
| yolo_detection | 23 | 23 | 0 | 158.9743 | 142.8149 | 1323.5524 |

## Interaction Window

- Whisper burst window: 8.0095s -> 11.8557s

### YOLO

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 3 | 503.8027 | 1202.5086 | 1323.5524 |
| During Whisper | 4 | 85.237 | 112.1317 | 113.9455 |
| After Whisper | 16 | 112.7533 | 137.3086 | 143.662 |

### FastAPI ResNet18

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 130 | 68.367 | 94.623 | 695.5833 |
| During Whisper | 52 | 100.392 | 139.7201 | 771.9765 |
| After Whisper | 353 | 52.4732 | 64.857 | 103.3148 |

## Boundary

- This is multi-workload runtime interaction evidence, not a production stress test.
- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.
- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.
- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.
