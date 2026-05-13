# System Baseline Smoke Report

> Day 1 환경 점검 이후 같은 Jetson에서 실행한 system smoke benchmark 요약입니다.
> 이 결과는 deployment readiness가 아니라 이후 실험을 해석하기 위한 작은 기준선입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-13T12:28:06+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Python | 3.10.12 |
| Result JSON | `results/system/system_baseline_20260513_122758.json` |
| Tegrastats log | `artifacts/system/tegrastats_system_baseline_20260513_122758.log` |
| Power mode | NV Power Mode: 25W; 1 |
| Git commit | ed18b65 |

## Parameters

| Field | Value |
|---|---|
| repeat | 5 |
| warmup | 1 |
| matmul size | 512 x 512 |
| CPU loop iterations | 2000000 |
| disk smoke size | 64 MiB |

## Results

| Benchmark | Status | Mean ms | P95 ms | Unit |
|---|---:|---:|---:|---|
| `cpu_python_loop` | ok | 516.7891 | 536.5952 | milliseconds |
| `numpy_matmul` | ok | 2.9245 | 3.953 | milliseconds |
| `torch_cpu_matmul` | ok | 4.0727 | 4.4538 | milliseconds |
| `torch_cuda_matmul` | ok | 1.8951 | 1.9109 | milliseconds |
| `disk_write_read_smoke` | ok | 127.1347 | 127.6417 | milliseconds |

## Notes

- PyTorch CUDA matmul is a smoke measurement only; it is not an inference benchmark.
- Disk smoke writes and reads a temporary file under the system temp directory, then deletes it.
- Backend, power mode, and precision must stay attached to these numbers before comparing them with future runs.
- `tegrastats` was captured as a side log during the benchmark, so thermal/power context can be inspected separately.
