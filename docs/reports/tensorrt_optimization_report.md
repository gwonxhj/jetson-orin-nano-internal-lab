# TensorRT Optimization Smoke Report

> ResNet18 ONNX export와 TensorRT FP16 engine build/run smoke evidence입니다.
> 이 비교는 PyTorch CUDA FP32와 TensorRT FP16의 runtime comparison이며, precision/runtime이 다르므로 direct regression 판정으로 사용하지 않습니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T12:54:18+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Result JSON | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` |
| Build log | `artifacts/tensorrt/resnet18_fp16_build_20260513_125323.log` |
| Run log | `artifacts/tensorrt/resnet18_fp16_run_20260513_125323.log` |
| Tegrastats log | `artifacts/system/tegrastats_tensorrt_resnet18_20260513_125323.log` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | 34d04fc |

## Artifacts

| Artifact | Path | SHA256 | Size bytes |
|---|---|---|---:|
| ONNX | `models/resnet18_random_seed42_opset17.onnx` | `be389e1e7b40df969a7a63789549f022fc0245c64fcc09539ea09e8b2c75229e` | 46733664 |
| TensorRT engine | `artifacts/engines/resnet18_fp16_20260513_125323.engine` | `96bfefadbeb9722591b545415acf09aa338aaadf357b5cadf8e567ec5aad8cea` | 23774884 |

## Commands

```bash
/usr/src/tensorrt/bin/trtexec --onnx=models/resnet18_random_seed42_opset17.onnx --saveEngine=artifacts/engines/resnet18_fp16_20260513_125323.engine --fp16
/usr/src/tensorrt/bin/trtexec --loadEngine=artifacts/engines/resnet18_fp16_20260513_125323.engine --warmUp=500 --iterations=100
```

## Model / Protocol

| Field | Value |
|---|---|
| Source framework | pytorch |
| Runtime | tensorrt |
| Architecture | resnet18 |
| Weights | random_seeded_weights_no_pretrained_accuracy_claim |
| Canonical model hash | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` |
| Input shape | [1, 3, 224, 224] |
| Batch size | 1 |
| Precision | fp16 |
| Warmup | 500 ms |
| Iterations | 100 |
| Preprocessing included | False |
| Postprocessing included | False |

## TensorRT Metrics

| Metric | Value |
|---|---:|
| Throughput qps | 1134.83 |
| Latency mean ms | 0.926784 |
| Latency median ms | 0.926514 |
| Latency p95 ms | 0.932251 |
| Latency p99 ms | 0.936035 |
| GPU compute mean ms | 0.878035 |
| GPU compute p95 ms | 0.881104 |
| H2D mean ms | 0.0416764 |
| D2H mean ms | 0.00707177 |

## Runtime Comparison Context

| Runtime | Precision | Input | Model hash | Mean latency ms | P95 latency ms | Notes |
|---|---|---|---|---:|---:|---|
| PyTorch CUDA | FP32 | synthetic `[1, 3, 224, 224]` | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` | 11.6289 | 16.3123 | eager PyTorch smoke |
| TensorRT | FP16 | static `[1, 3, 224, 224]` | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` | 0.926784 | 0.932251 | `trtexec` engine smoke |

Approximate mean-latency ratio: `12.55x` TensorRT/PyTorch runtime difference under this smoke setup.

## Notes

- Random seeded weights mean this result is not ImageNet accuracy evidence.
- TensorRT FP16 and PyTorch FP32 differ in precision and runtime, so the comparison is an optimization smoke, not a direct regression verdict.
- ONNX export uses a static input shape; `--shapes` is intentionally not passed to `trtexec` because TensorRT rejects explicit shapes for this static model.
- Build/run logs and hashes are preserved so the engine can be traced back to the source ONNX and command line.
