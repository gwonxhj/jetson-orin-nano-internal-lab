# Multi-Workload Sustained Runtime Report

> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst run together as runtime interaction evidence.
> This report is constrained Jetson runtime behavior evidence, not production stress or deployment-ready proof.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-18T02:35:59+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18086` |
| Duration | 120.1017 s |
| Server log | `artifacts/system/fastapi_multi_workload_degradation_server_20260518_023351.log` |
| Tegrastats log | `artifacts/system/tegrastats_multi_workload_degradation_20260518_023351.log` |
| Mock workloads | False |

## Workload Summary

| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 6058 | 6058 | 0 | 147.3829 | 181.4991 | 950.5697 |
| fastapi_whisper | 2 | 2 | 0 | 5799.7609 | 8377.5258 | 8663.9441 |
| yolo_detection | 291 | 291 | 0 | 145.8958 | 177.8141 | 1718.432 |

## Interaction Window

- Whisper burst window: 30.0391s -> 86.6837s

### YOLO

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 60 | 167.823 | 176.78 | 1718.432 |
| During Whisper | 146 | 139.0962 | 175.5125 | 374.1414 |
| After Whisper | 85 | 142.0972 | 180.5163 | 187.5506 |

### FastAPI ResNet18

| Window | Count | Mean ms | P95 ms | Max ms |
|---|---:|---:|---:|---:|
| Before Whisper | 1536 | 144.4115 | 172.3518 | 836.4011 |
| During Whisper | 2802 | 151.0955 | 198.0787 | 950.5697 |
| After Whisper | 1720 | 143.9884 | 169.5231 | 468.115 |

## Serving Observability

| Signal | Value |
|---|---:|
| Client completed requests | 6060 |
| Client failed requests | 0 |
| Client max outstanding sum | 9 |
| Server max in-flight requests | 9 |
| Server failed requests | 0 |
| Dropped request count proxy | 0 |

These counters are queue/backlog proxies for localhost evidence; they are not production queue-depth telemetry.

## Boundary

- This is multi-workload runtime interaction evidence, not a production stress test.
- Latency spikes, request errors, backlog, or dependency failures are reliability signals and should be preserved.
- Results must be interpreted with power mode, backend/provider, duration, workload mix, and telemetry context.
- The scenario uses local file/audio/synthetic inputs and does not require external cameras, sensors, microphones, motors, or robot hardware.
