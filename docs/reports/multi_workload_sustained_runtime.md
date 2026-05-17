# Multi-Workload Sustained Runtime Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.
> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-18T00:59:18+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18085` |
| Duration | 1800.0892 s |
| Server log | `artifacts/system/fastapi_multi_workload_server_20260518_002910.log` |
| Tegrastats log | `artifacts/system/tegrastats_multi_workload_20260518_002910.log` |
| Mock workloads | False |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 34324 | 34324 | 0 | 54.2977 | 68.0591 | 785.0608 |
| fastapi_whisper | 5 | 5 | 0 | 1313.5877 | 3521.1574 | 4243.5182 |
| yolo_detection | 1606 | 1606 | 0 | 117.7534 | 144.4643 | 1341.9493 |

## Interaction Window

- Whisper burst window: 300.0338s -> 1506.832s

### YOLO

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 264 | 123.133 | 146.4491 | 1341.9493 |
| During Whisper | 1080 | 116.3743 | 144.2472 | 255.9929 |
| After Whisper | 262 | 118.0177 | 143.8846 | 347.2609 |

### FastAPI ResNet18

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 5688 | 54.8157 | 69.4149 | 678.3729 |
| During Whisper | 23054 | 54.1282 | 67.3912 | 785.0608 |
| After Whisper | 5582 | 54.4698 | 68.5984 | 340.3874 |

## Boundary

- This is multi-workload runtime interaction evidence, not a production stress test.
- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.
- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.
- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.
