# Multi-Workload Sustained Runtime Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.
> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-17T22:21:24+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18085` |
| Duration | 600.0216 s |
| Server log | `artifacts/system/fastapi_multi_workload_server_20260517_221116.log` |
| Tegrastats log | `artifacts/system/tegrastats_multi_workload_20260517_221116.log` |
| Mock workloads | False |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 11388 | 11388 | 0 | 54.7348 | 67.6168 | 696.8211 |
| fastapi_whisper | 3 | 3 | 0 | 1709.1628 | 3604.4617 | 3934.7886 |
| yolo_detection | 533 | 533 | 0 | 118.0908 | 143.6312 | 1331.9266 |

## Interaction Window

- Whisper burst window: 120.0324s -> 365.3563s

### YOLO

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 103 | 129.3904 | 143.5295 | 1331.9266 |
| During Whisper | 220 | 114.6859 | 144.3394 | 149.0473 |
| After Whisper | 210 | 116.1157 | 143.113 | 148.9029 |

### FastAPI ResNet18

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 2272 | 55.0199 | 69.6106 | 696.8211 |
| During Whisper | 4639 | 55.1439 | 67.6024 | 694.1111 |
| After Whisper | 4477 | 54.1661 | 66.8783 | 98.7794 |

## Boundary

- This is multi-workload runtime interaction evidence, not a production stress test.
- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.
- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.
- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.
