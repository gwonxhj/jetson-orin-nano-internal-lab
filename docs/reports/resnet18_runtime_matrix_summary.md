# ResNet18 Runtime Matrix Summary

> ResNet18 synthetic input smoke 결과를 runtime/provider/cache 관점으로 한 장에 묶은 요약입니다. 이 문서는 deployment-ready 주장이나 accuracy evidence가 아니라, 같은 model hash와 input shape를 기준으로 실행 경로 차이를 설명하는 portfolio evidence입니다.

## Baseline Conditions

| Field | Value |
|---|---|
| Board scope | Jetson Orin Nano internal-only lab |
| Model | ResNet18, random seeded weights |
| Model hash | `9300a6d687232af2e17af0afba72d35cfc0e828fb3cd519aa72e1bb873b72245` |
| Input shape | `[1, 3, 224, 224]` |
| Input source | synthetic random array |
| Power mode | 25W |
| Direct regression? | No. Backend/provider/precision differ, so this is runtime comparison evidence. |

## Runtime Matrix

| Runtime path | Provider / tool | Precision | Mean ms | P95 ms | What it shows |
|---|---|---|---:|---:|---|
| PyTorch eager | CUDA | FP32 | 11.6289 | 16.3123 | Framework baseline on GPU |
| ONNX Runtime | CPUExecutionProvider | FP32 | 42.2252 | 44.6845 | ONNX CPU fallback path |
| ONNX Runtime | CUDAExecutionProvider | FP32 | 6.7277 | 7.3183 | ONNX GPU provider path |
| ONNX Runtime | TensorrtExecutionProvider | FP32 | 4.0276 | 5.4686 | ORT TensorRT provider integration |
| Native TensorRT | `trtexec` | FP16 | 0.926784 | 0.932251 | Explicit TensorRT FP16 engine path |

## Relative View

| Comparison | Mean latency ratio |
|---|---:|
| ONNX Runtime CPU / ONNX Runtime CUDA | 6.2763x |
| ONNX Runtime CUDA / ONNX Runtime TensorRT | 1.6704x |
| ONNX Runtime TensorRT / native TensorRT FP16 | 4.3458x |
| PyTorch CUDA / native TensorRT FP16 | 12.5476x |
| ONNX Runtime CPU / native TensorRT FP16 | 45.561x |

## TensorRT EP Cache Split

| Phase | Session create ms | First run ms | Repeated mean ms | Repeated P95 ms | Meaning |
|---|---:|---:|---:|---:|---|
| Cold build | 24489.9395 | 8.2652 | 4.1027 | 5.5288 | Cache directory cleared before session creation |
| Warm cache | 2175.843 | 6.7976 | 4.0811 | 5.4887 | Same provider options reused after cache artifact exists |

Provider options used:

| Option | Value |
|---|---|
| `trt_engine_cache_enable` | `True` |
| `trt_engine_cache_path` | `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32` |
| `trt_engine_cache_prefix` | `resnet18_fp32` |
| `trt_fp16_enable` | `False` |

Cache artifact:

- `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32/resnet18_fp32_12793127510422195378_0_sm87.engine`

## Interpretation

- PyTorch CUDA is the framework baseline; it proves GPU execution through PyTorch, not deployment optimization.
- ONNX Runtime CPU is useful as a portability/fallback signal, but it is not comparable to GPU providers as a regression target.
- ONNX Runtime CUDA shows the ONNX graph can execute through ORT GPU provider after the isolated `ort_cuda_env` install.
- ONNX Runtime TensorRT EP improves over ORT CUDA in repeated `session.run` latency, while still staying inside ORT provider integration.
- Native TensorRT `trtexec` FP16 remains the fastest path here, but it differs in runtime surface, precision, build protocol, and engine lifecycle.
- TensorRT EP cache mainly reduces session creation cost in this smoke; repeated run latency is similar between cold-built and warm-cache sessions.

## Source Evidence

| Evidence | Path |
|---|---|
| PyTorch CUDA smoke | `results/inference/pytorch_resnet18_20260513_125245.json` |
| ONNX Runtime CPU smoke | `results/inference/onnxruntime_resnet18_cpu_20260514_013723.json` |
| ONNX Runtime CUDA EP | `results/inference/onnxruntime_cuda_ep_attempt_20260514_023545.json` |
| ONNX Runtime TensorRT EP | `results/inference/onnxruntime_tensorrt_ep_attempt_20260514_025120.json` |
| ONNX Runtime TensorRT cache | `results/inference/onnxruntime_tensorrt_cache_bench_20260514_030413.json` |
| Native TensorRT FP16 | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` |
| 5-way runtime comparison | `results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_onnxruntime_cuda_fp32_vs_onnxruntime_tensorrt_fp32_vs_tensorrt_fp16_20260514_025504.json` |
