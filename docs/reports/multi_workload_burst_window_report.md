# Multi-Workload Burst Window Report

> Whisper burst 전/중/후 window별 workload latency와 `tegrastats` telemetry 변화를 정리한 보고서입니다.
> 이 보고서는 runtime reliability signal 분석용이며 production stress test나 deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_sustained_20260518_002910.json` |
| Timeline JSON | `results/runtime_compare/multi_workload_timeline_20260518_002910.json` |
| Before window | 60.0 s |
| After window | 60.0 s |
| Burst count | 5 |

## Aggregate Latency By Phase

| Phase | Workload | Events | P50 ms | P95 ms | P99 ms | Max ms | Errors |
|---|---|---:|---:|---:|---:|---:|---:|
| before | fastapi_resnet18 | 5702 | 53.5299 | 68.0136 | 83.7897 | 94.8332 | 0 |
| before | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| before | yolo_detection | 268 | 115.5444 | 143.8888 | 147.3715 | 149.413 | 0 |
| during | fastapi_resnet18 | 102 | 49.001 | 177.8823 | 432.8287 | 785.0608 | 0 |
| during | fastapi_whisper | 5 | 598.1001 | 3521.1574 | 4099.046 | 4243.5182 | 0 |
| during | yolo_detection | 7 | 109.0663 | 114.1083 | 114.2063 | 114.2308 | 0 |
| after | fastapi_resnet18 | 5818 | 53.3284 | 65.5952 | 82.7925 | 102.0006 | 0 |
| after | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| after | yolo_detection | 268 | 115.5403 | 143.8211 | 146.7603 | 148.596 | 0 |

## Aggregate Telemetry By Phase

| Phase | Samples | GR3D avg % | CPU avg % | RAM avg MB | GPU temp max C | VDD_IN avg mW |
|---|---:|---:|---:|---:|---:|---:|
| before | 347 | 34.384 | 12.868 | 3444.917 | 45.343 | 5626.243 |
| during | 49 | 35.573 | 15.373 | 3515.489 | 45.281 | 5758.698 |
| after | 348 | 35.467 | 12.937 | 3561.281 | 45.406 | 5639.692 |

## Aggregate Deltas

| Delta | Metric | Value |
|---|---|---:|
| during_minus_before_latency_ms | fastapi_resnet18.p50 | -4.5289 |
| during_minus_before_latency_ms | fastapi_resnet18.p95 | 109.8687 |
| during_minus_before_latency_ms | fastapi_resnet18.p99 | 349.039 |
| during_minus_before_latency_ms | fastapi_resnet18.max | 690.2276 |
| during_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.max | n/a |
| during_minus_before_latency_ms | yolo_detection.p50 | -6.4781 |
| during_minus_before_latency_ms | yolo_detection.p95 | -29.7805 |
| during_minus_before_latency_ms | yolo_detection.p99 | -33.1652 |
| during_minus_before_latency_ms | yolo_detection.max | -35.1822 |
| after_minus_before_latency_ms | fastapi_resnet18.p50 | -0.2015 |
| after_minus_before_latency_ms | fastapi_resnet18.p95 | -2.4184 |
| after_minus_before_latency_ms | fastapi_resnet18.p99 | -0.9972 |
| after_minus_before_latency_ms | fastapi_resnet18.max | 7.1674 |
| after_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.max | n/a |
| after_minus_before_latency_ms | yolo_detection.p50 | -0.0041 |
| after_minus_before_latency_ms | yolo_detection.p95 | -0.0677 |
| after_minus_before_latency_ms | yolo_detection.p99 | -0.6112 |
| after_minus_before_latency_ms | yolo_detection.max | -0.817 |
| during_minus_before_telemetry | ram_used_mb_avg | 70.572 |
| during_minus_before_telemetry | ram_used_mb_max | 0.0 |
| during_minus_before_telemetry | gr3d_freq_pct_avg | 1.189 |
| during_minus_before_telemetry | gr3d_freq_pct_max | 0.0 |
| during_minus_before_telemetry | cpu_busy_pct_avg | 2.505 |
| during_minus_before_telemetry | cpu_busy_pct_max | 0.0 |
| during_minus_before_telemetry | gpu_temp_c_max | -0.062 |
| during_minus_before_telemetry | vdd_in_mw_avg | 132.455 |
| during_minus_before_telemetry | vdd_in_mw_max | 0.0 |
| after_minus_before_telemetry | ram_used_mb_avg | 116.364 |
| after_minus_before_telemetry | ram_used_mb_max | 36.0 |
| after_minus_before_telemetry | gr3d_freq_pct_avg | 1.083 |
| after_minus_before_telemetry | gr3d_freq_pct_max | 0.0 |
| after_minus_before_telemetry | cpu_busy_pct_avg | 0.069 |
| after_minus_before_telemetry | cpu_busy_pct_max | 0.0 |
| after_minus_before_telemetry | gpu_temp_c_max | 0.063 |
| after_minus_before_telemetry | vdd_in_mw_avg | 13.449 |
| after_minus_before_telemetry | vdd_in_mw_max | 0.0 |

## Per-Burst Summary

| Burst | Phase | FastAPI p99 ms | YOLO p99 ms | Whisper max ms | GR3D avg % | CPU avg % |
|---:|---|---:|---:|---:|---:|---:|
| 0 | before | 84.5087 | 147.3498 | n/a | 37.114 | 13.379 |
| 0 | during | 588.031 | 114.2186 | 4243.5182 | 38.2 | 18.967 |
| 0 | after | 78.9757 | 144.9735 | n/a | 34.841 | 13.375 |
| 1 | before | 83.8251 | 148.339 | n/a | 37.543 | 12.838 |
| 1 | during | 70.9781 | n/a | 598.1001 | 21.0 | 14.9 |
| 1 | after | 79.1864 | 142.8203 | n/a | 33.643 | 13.045 |
| 2 | before | 84.0626 | 145.7428 | n/a | 31.159 | 12.768 |
| 2 | during | 85.6478 | 102.5846 | 539.4265 | 32.6 | 14.283 |
| 2 | after | 80.2698 | 146.238 | n/a | 35.814 | 12.793 |
| 3 | before | 85.2245 | 146.1189 | n/a | 30.254 | 12.694 |
| 3 | during | 71.3325 | 97.0518 | 631.7141 | 42.4 | 14.55 |
| 3 | after | 86.7585 | 146.5683 | n/a | 41.971 | 12.757 |
| 4 | before | 79.6011 | 142.8128 | n/a | 35.852 | 12.662 |
| 4 | during | 75.0833 | 112.3726 | 555.1795 | 43.667 | 14.167 |
| 4 | after | 83.84 | 147.6145 | n/a | 31.067 | 12.717 |

## Boundary

- Latency windows are event-level summaries around Whisper bursts.
- Telemetry windows are compact timeline-bucket summaries, not raw sensor replay.
- Treat spikes and deltas as runtime reliability signals, not deployment capacity proof.
