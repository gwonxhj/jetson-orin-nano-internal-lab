# ONNX Runtime Inference Smoke Report

> ResNet18 ONNX artifact를 ONNX Runtime으로 실행한 smoke evidence입니다.
> Provider availability를 별도로 기록하며, 이 결과는 runtime path evidence이지 accuracy evidence가 아닙니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T01:37:26+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| ONNX Runtime | 1.23.2 |
| Requested provider | `CPUExecutionProvider` |
| Available providers | `['AzureExecutionProvider', 'CPUExecutionProvider']` |
| CUDA provider available | False |
| Power mode | NV Power Mode: 25W; 1 |
| Result JSON | `results/inference/onnxruntime_resnet18_cpu_20260514_013723.json` |
| Tegrastats log | `artifacts/system/tegrastats_onnxruntime_resnet18_20260514_013723.log` |

## Parameters

| Field | Value |
|---|---:|
| input shape | [1, 3, 224, 224] |
| precision | fp32 |
| warmup | 10 |
| repeat | 50 |

## Results

| Runtime | Provider | Mean ms | P95 ms | P99 ms |
|---|---|---:|---:|---:|
| ONNX Runtime | CPUExecutionProvider | 42.2252 | 44.6845 | 46.1999 |

## Interpretation

- ONNX Runtime CPUExecutionProvider is runnable in the current Jetson Python environment.
- CUDAExecutionProvider is not available in this ONNX Runtime build, so ORT CUDA is recorded as unavailable rather than inferred from PyTorch CUDA availability.
- This smoke uses synthetic input and random seeded model weights; it is not an accuracy claim.
- PyTorch CUDA, ONNX Runtime CPU, and TensorRT FP16 differ in backend/provider/precision, so the comparison should remain runtime comparison evidence, not direct regression evidence.
