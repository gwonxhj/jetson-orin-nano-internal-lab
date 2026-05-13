# ONNX Runtime CUDA EP Activation Attempt

> 격리 원칙을 유지하면서 ONNX Runtime CUDAExecutionProvider 활성화 가능 여부를 기록한 evidence입니다.
> 성공, 실패, unavailable 상태를 모두 정상적인 실험 결과로 남깁니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T01:50:52+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Python | `python3 (yolo_env)` / 3.10.12 |
| ONNX Runtime | 1.23.2 |
| PyTorch | 2.8.0 |
| Torch CUDA available | True |
| Available ORT providers | `['AzureExecutionProvider', 'CPUExecutionProvider']` |
| Result JSON | `results/inference/onnxruntime_cuda_ep_attempt_20260514_015048.json` |

## Isolation Policy

| Field | Value |
|---|---|
| Existing env modified | False |
| Install command executed | False |
| Intended install target | `separate conda/venv or Docker image` |
| Preload strategy | `import torch before onnxruntime` |

## Activation Result

| Field | Value |
|---|---|
| Requested provider | `CUDAExecutionProvider` |
| Requested provider available | False |
| Activation status | `unavailable` |
| Session providers | `[]` |
| Failure reason | `CUDAExecutionProvider is not in available_providers` |
| Mean ms | not measured |
| P95 ms | not measured |

## Interpretation

- This script does not install packages or modify the current environment.
- If CUDAExecutionProvider is unavailable, the next step is an isolated conda/venv or Docker install attempt rather than changing `yolo_env` in place.
- If activation succeeds, the measured latency can become the ONNX Runtime CUDA candidate for the runtime comparison matrix.
- This evidence remains runtime/provider validation, not deployment readiness or accuracy evidence.
