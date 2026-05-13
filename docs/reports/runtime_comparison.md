# Runtime Comparison Report

> ResNet18 PyTorch CUDA FP32와 TensorRT FP16 smoke 결과를 비교합니다.
> precision/runtime이 다르므로 direct regression이 아니라 runtime comparison evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T13:11:15+09:00 |
| Hostname | `jetson-orin-nano` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | 87b6c6d |
| PyTorch source | `results/inference/pytorch_resnet18_20260513_125245.json` |
| TensorRT source | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` |

## Comparability

| Check | Value |
|---|---:|
| Same model hash | True |
| Same input shape | True |
| Same precision | False |
| Same pre/post scope | True |
| Verdict | `runtime_comparison_not_direct_regression` |

## Runtime Results

| Runtime | Precision | Input shape | Mean ms | P95 ms | P99 ms | Throughput qps |
|---|---|---|---:|---:|---:|---:|
| PyTorch CUDA | fp32 | [1, 3, 224, 224] | 11.6289 | 16.3123 | 16.7595 | n/a |
| TensorRT trtexec | fp16 | [1, 3, 224, 224] | 0.926784 | 0.932251 | 0.936035 | 1134.83 |

## Ratios

| Ratio | Value |
|---|---:|
| Mean latency PyTorch / TensorRT | 12.5476x |
| P95 latency PyTorch / TensorRT | 17.4978x |

## Notes

- PyTorch uses CUDA FP32 eager execution while TensorRT uses FP16 trtexec engine execution.
- The model hash and input shape match, but precision and runtime differ.
- Synthetic input is used; preprocessing and accuracy are outside this comparison.
- PyTorch top-5 output summary is computed after timed inference and is not included in latency.
- TensorRT engine and ONNX hashes are preserved in the comparison JSON.
- Synthetic input is used, so this is runtime evidence, not model quality evidence.
