# Runtime Comparison Report

> ResNet18 PyTorch CUDA FP32, ONNX Runtime CPU FP32, TensorRT FP16 smoke 결과를 비교합니다.
> backend/provider/precision이 다르면 direct regression이 아니라 runtime comparison evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T01:38:14+09:00 |
| Hostname | `jetson-orin-nano` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | d22ffa1 |
| pytorch source | `results/inference/pytorch_resnet18_20260513_125245.json` |
| tensorrt source | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` |
| onnxruntime source | `results/inference/onnxruntime_resnet18_cpu_20260514_013723.json` |

## Comparability

| Check | Value |
|---|---:|
| Same model hash | True |
| Same input shape | True |
| Same precision | False |
| Same pre/post scope | True |
| Verdict | `runtime_comparison_not_direct_regression` |

## Runtime Results

| Runtime | Backend / Provider | Precision | Input shape | Mean ms | P95 ms | P99 ms | Throughput qps |
|---|---|---|---|---:|---:|---:|---:|
| PyTorch CUDA | cuda | fp32 | [1, 3, 224, 224] | 11.6289 | 16.3123 | 16.7595 | n/a |
| ONNX Runtime CPU | CPUExecutionProvider | fp32 | [1, 3, 224, 224] | 42.2252 | 44.6845 | 46.1999 | n/a |
| TensorRT trtexec | trtexec | fp16 | [1, 3, 224, 224] | 0.926784 | 0.932251 | 0.936035 | 1134.83 |

## Ratios

| Ratio | Value |
|---|---:|
| mean_latency_pytorch_over_tensorrt | 12.5476x |
| p95_latency_pytorch_over_tensorrt | 17.4978x |
| mean_latency_pytorch_over_onnxruntime | 0.2754x |
| p95_latency_pytorch_over_onnxruntime | 0.3651x |
| mean_latency_onnxruntime_over_tensorrt | 45.561x |
| p95_latency_onnxruntime_over_tensorrt | 47.9318x |

## Notes

- PyTorch uses CUDA FP32 eager execution while TensorRT uses FP16 trtexec engine execution.
- The model hash and input shape match, but precision and runtime differ.
- Synthetic input is used; preprocessing and accuracy are outside this comparison.
- PyTorch top-5 output summary is computed after timed inference and is not included in latency.
- ONNX Runtime CPUExecutionProvider is included as a third runtime using the same ONNX artifact.
- ONNX Runtime CUDAExecutionProvider available: False.
- ONNX Runtime CPU and PyTorch CUDA are different providers, so their latency is not a direct regression comparison.
- TensorRT engine and ONNX hashes are preserved in the comparison JSON.
- Synthetic input is used, so this is runtime evidence, not model quality evidence.
