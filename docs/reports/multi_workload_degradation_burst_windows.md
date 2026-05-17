# Multi-Workload Burst Window Report

> Whisper burst 전/중/후 window별 workload latency와 `tegrastats` telemetry 변화를 정리한 보고서입니다.
> 이 보고서는 runtime reliability signal 분석용이며 production stress test나 deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_013625.json` |
| Timeline JSON | `results/runtime_compare/multi_workload_degradation_timeline_20260518_013625.json` |
| Before window | 30.0 s |
| After window | 30.0 s |
| Burst count | 3 |

## Aggregate Latency By Phase

| Phase | Workload | Events | P50 ms | P95 ms | P99 ms | Max ms | Errors |
|---|---|---:|---:|---:|---:|---:|---:|
| before | fastapi_resnet18 | 4728 | 139.8037 | 167.9633 | 184.757 | 494.8059 | 0 |
| before | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| before | yolo_detection | 229 | 139.6581 | 171.4847 | 179.753 | 184.8861 | 0 |
| during | fastapi_resnet18 | 609 | 158.3304 | 269.3387 | 763.7099 | 883.8447 | 0 |
| during | fastapi_whisper | 3 | 2937.1685 | 8787.4625 | 9307.4887 | 9437.4952 | 0 |
| during | yolo_detection | 39 | 123.9183 | 157.5483 | 169.7481 | 171.2616 | 0 |
| after | fastapi_resnet18 | 4709 | 141.0344 | 169.4753 | 186.9956 | 478.9289 | 0 |
| after | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| after | yolo_detection | 229 | 139.9851 | 175.7903 | 185.1431 | 189.2701 | 0 |

## Aggregate Telemetry By Phase

| Phase | Samples | GR3D avg % | CPU avg % | RAM avg MB | GPU temp max C | VDD_IN avg mW |
|---|---:|---:|---:|---:|---:|---:|
| before | 105 | 52.467 | 40.068 | 3406.038 | 48.843 | 8092.81 |
| during | 24 | 54.21 | 40.075 | 3490.32 | 48.562 | 7892.29 |
| after | 103 | 55.883 | 39.651 | 3626.638 | 49.156 | 8078.7 |

## Aggregate Deltas

| Delta | Metric | Value |
|---|---|---:|
| during_minus_before_latency_ms | fastapi_resnet18.p50 | 18.5267 |
| during_minus_before_latency_ms | fastapi_resnet18.p95 | 101.3754 |
| during_minus_before_latency_ms | fastapi_resnet18.p99 | 578.9529 |
| during_minus_before_latency_ms | fastapi_resnet18.max | 389.0388 |
| during_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.max | n/a |
| during_minus_before_latency_ms | yolo_detection.p50 | -15.7398 |
| during_minus_before_latency_ms | yolo_detection.p95 | -13.9364 |
| during_minus_before_latency_ms | yolo_detection.p99 | -10.0049 |
| during_minus_before_latency_ms | yolo_detection.max | -13.6245 |
| after_minus_before_latency_ms | fastapi_resnet18.p50 | 1.2307 |
| after_minus_before_latency_ms | fastapi_resnet18.p95 | 1.512 |
| after_minus_before_latency_ms | fastapi_resnet18.p99 | 2.2386 |
| after_minus_before_latency_ms | fastapi_resnet18.max | -15.877 |
| after_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.max | n/a |
| after_minus_before_latency_ms | yolo_detection.p50 | 0.327 |
| after_minus_before_latency_ms | yolo_detection.p95 | 4.3056 |
| after_minus_before_latency_ms | yolo_detection.p99 | 5.3901 |
| after_minus_before_latency_ms | yolo_detection.max | 4.384 |
| during_minus_before_telemetry | ram_used_mb_avg | 84.282 |
| during_minus_before_telemetry | ram_used_mb_max | 0.0 |
| during_minus_before_telemetry | gr3d_freq_pct_avg | 1.743 |
| during_minus_before_telemetry | gr3d_freq_pct_max | 1.0 |
| during_minus_before_telemetry | cpu_busy_pct_avg | 0.007 |
| during_minus_before_telemetry | cpu_busy_pct_max | 0.0 |
| during_minus_before_telemetry | gpu_temp_c_max | -0.281 |
| during_minus_before_telemetry | vdd_in_mw_avg | -200.52 |
| during_minus_before_telemetry | vdd_in_mw_max | 0.0 |
| after_minus_before_telemetry | ram_used_mb_avg | 220.6 |
| after_minus_before_telemetry | ram_used_mb_max | 0.0 |
| after_minus_before_telemetry | gr3d_freq_pct_avg | 3.416 |
| after_minus_before_telemetry | gr3d_freq_pct_max | 1.0 |
| after_minus_before_telemetry | cpu_busy_pct_avg | -0.417 |
| after_minus_before_telemetry | cpu_busy_pct_max | -12.0 |
| after_minus_before_telemetry | gpu_temp_c_max | 0.313 |
| after_minus_before_telemetry | vdd_in_mw_avg | -14.11 |
| after_minus_before_telemetry | vdd_in_mw_max | 0.0 |

## Per-Burst Summary

| Burst | Phase | FastAPI p99 ms | YOLO p99 ms | Whisper max ms | GR3D avg % | CPU avg % |
|---:|---|---:|---:|---:|---:|---:|
| 0 | before | 177.9009 | 184.1369 | n/a | 54.714 | 40.171 |
| 0 | during | 782.8628 | 170.3057 | 9437.4952 | 53.425 | 38.688 |
| 0 | after | 194.5254 | 181.9502 | n/a | 62.064 | 39.135 |
| 1 | before | 186.9247 | 176.8973 | n/a | 51.4 | 40.043 |
| 1 | during | 205.2464 | 142.8002 | 2937.1685 | 54.9 | 41.25 |
| 1 | after | 186.8876 | 180.03 | n/a | 50.143 | 39.757 |
| 2 | before | 192.7222 | 176.0453 | n/a | 51.286 | 39.99 |
| 2 | during | 196.7487 | 155.7378 | 2177.9319 | 54.4 | 40.5 |
| 2 | after | 180.2766 | 189.2232 | n/a | 55.443 | 40.061 |

## Boundary

- Latency windows are event-level summaries around Whisper bursts.
- Telemetry windows are compact timeline-bucket summaries, not raw sensor replay.
- Treat spikes and deltas as runtime reliability signals, not deployment capacity proof.
