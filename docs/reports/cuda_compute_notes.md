# CUDA Compute Smoke Notes

> 모델 추론이 아닌 Jetson 내부 GPU compute와 host/device transfer 비용을 분리해서 기록한 smoke evidence입니다.
> 이 결과는 deployment readiness가 아니라 이후 inference/runtime 수치를 해석하기 위한 작은 기준선입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T15:11:39+09:00 |
| Device | Jetson Orin Nano |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Python | 3.10.12 |
| Torch | 2.8.0 |
| CUDA available | True |
| CUDA device | Orin |
| Power mode | NV Power Mode: 25W; 1 |
| Tegrastats log | `artifacts/system/tegrastats_cuda_compute_20260513_151135.log` |

## Parameters

| Field | Value |
|---|---:|
| repeat | 5 |
| warmup | 1 |
| matmul size | 1024 x 1024 |
| vector elements | 4194304 |
| transfer size | 32 MiB |

## Results

| Benchmark | Category | Device / Direction | Mean ms | P95 ms | Transfer MiB/s |
|---|---|---|---:|---:|---:|
| `torch_cpu_matmul` | compute | cpu | 24.5775 | 26.7218 |  |
| `torch_cuda_matmul` | compute | cuda | 5.9287 | 6.3484 |  |
| `cuda_elementwise_add` | compute | cuda | 1.8185 | 1.8699 |  |
| `cuda_h2d_transfer` | transfer | h2d | 6.2421 | 6.4006 | 5126.4799 |
| `cuda_d2h_transfer` | transfer | d2h | 11.5013 | 11.6109 | 2782.2942 |

## Interpretation

- This is a compute/transfer smoke, not a model inference benchmark.
- CPU and GPU numbers should be interpreted with input size and synchronization overhead attached.
- Host/device transfer cost is recorded separately because small workloads can be dominated by movement rather than compute.
- Power mode and tegrastats side log must stay attached before comparing this run with future CUDA or inference runs.
- Short smoke results must not be used as sustained thermal throttling or deployment-readiness evidence.
