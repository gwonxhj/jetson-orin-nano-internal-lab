# ONNX Runtime TensorRT EP Engine Cache Report

> ONNX Runtime TensorRT EP provider option과 engine cache 조건을 명시하고, cold build와 warm cache 실행을 분리한 evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T03:04:46+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `ort_cuda_env` |
| ONNX Runtime | 1.23.0 |
| Available providers | `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']` |
| Result JSON | `results/inference/onnxruntime_tensorrt_cache_bench_20260514_030413.json` |

## Provider Options

| Option | Value |
|---|---|
| `trt_engine_cache_enable` | `True` |
| `trt_engine_cache_path` | `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32` |
| `trt_engine_cache_prefix` | `resnet18_fp32` |
| `trt_fp16_enable` | `False` |

## Cache Artifacts

| Field | Value |
|---|---|
| Cache path | `artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32` |
| Cache prefix | `resnet18_fp32` |
| Cache file count | 1 |

## Phase Results

| Phase | Session create ms | First run ms | Mean ms | P95 ms | Session providers |
|---|---:|---:|---:|---:|---|
| Cold build | 24489.9395 | 8.2652 | 4.1027 | 5.5288 | `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']` |
| Warm cache | 2175.843 | 6.7976 | 4.0811 | 5.4887 | `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']` |

## Interpretation

- Cold build clears the cache directory before session creation.
- Warm cache reuses the same provider options and cache directory after cold build has generated cache artifacts.
- Session creation time captures TensorRT EP build/cache load cost; repeated latency captures `session.run` after session creation.
- This remains runtime/provider/cache evidence, not deployment readiness or accuracy evidence.
