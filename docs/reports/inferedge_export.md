# InferEdge Export Report

> Runtime comparison evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `/home/risenano01/jetson-orin-nano-internal-lab/results/inferedge/resnet18_runtime_compare_20260513_133100/metadata.json` | Forge/Lab handoff metadata envelope |
| `/home/risenano01/jetson-orin-nano-internal-lab/results/inferedge/resnet18_runtime_compare_20260513_133100/result.json` | Lab-compatible Runtime result envelope with comparison evidence |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| compare key | `resnet18__b1__h224w224__fp16` |
| backend key | `tensorrt__jetson` |
| handoff ready | True |
| compare ready | True |
| verdict | `runtime_comparison_not_direct_regression` |

## Runtime Summary

| Metric | Value |
|---|---:|
| TensorRT mean ms | 0.926784 |
| TensorRT p95 ms | 0.932251 |
| TensorRT p99 ms | 0.936035 |
| TensorRT throughput qps | 1134.83 |
| PyTorch/TensorRT mean ratio | 12.5476x |

## Notes

- This is runtime comparison evidence, not a deployment approval.
- PyTorch CUDA FP32 and TensorRT FP16 differ in precision/runtime, so the comparison is not a direct regression verdict.
- The exported `result.json` keeps Lab-compatible top-level fields while preserving comparison details under `comparison`.
