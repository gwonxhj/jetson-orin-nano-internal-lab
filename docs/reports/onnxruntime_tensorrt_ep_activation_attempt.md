# ONNX Runtime TensorRT EP Activation Attempt

> 격리 원칙을 유지하면서 ONNX Runtime TensorrtExecutionProvider 활성화 가능 여부를 기록한 evidence입니다.
> 성공, 실패, unavailable 상태를 모두 정상적인 실험 결과로 남깁니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T02:55:02+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `ort_cuda_env` |
| Python | `python` / 3.10.20 |
| ONNX Runtime | 1.23.0 |
| PyTorch | unavailable |
| Torch CUDA available | False |
| Available ORT providers | `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']` |
| Result JSON | `results/inference/onnxruntime_tensorrt_ep_attempt_20260514_025120.json` |

## Isolation Policy

| Field | Value |
|---|---|
| Existing env modified | False |
| Install command executed by this runner | False |
| Intended install target | `separate conda/venv or Docker image` |
| Preload strategy | `import torch before onnxruntime` |

## Activation Result

| Field | Value |
|---|---|
| Requested provider | `TensorrtExecutionProvider` |
| Requested provider available | True |
| Activation status | `succeeded` |
| Session providers | `['TensorrtExecutionProvider', 'CPUExecutionProvider']` |
| Failure reason | `` |
| Mean ms | 4.0276 |
| P95 ms | 5.4686 |

## Interpretation

- This script does not install packages or modify the current environment.
- If TensorrtExecutionProvider is unavailable, the next step is an isolated conda/venv or Docker install attempt rather than changing `yolo_env` in place.
- If activation succeeds, the measured latency can become the ONNX Runtime TensorRT candidate for the runtime comparison matrix.
- This evidence remains runtime/provider validation, not deployment readiness or accuracy evidence.
