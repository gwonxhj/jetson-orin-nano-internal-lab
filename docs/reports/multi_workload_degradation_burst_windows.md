# Multi-Workload Burst Window Report

> Whisper burst 전/중/후 window별 workload latency와 `tegrastats` telemetry 변화를 정리한 보고서입니다.
> 이 보고서는 runtime reliability signal 분석용이며 production stress test나 deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_023351.json` |
| Timeline JSON | `results/runtime_compare/multi_workload_degradation_timeline_20260518_023351.json` |
| Before window | 30.0 s |
| After window | 30.0 s |
| Burst count | 2 |

## Aggregate Latency By Phase

| Phase | Workload | Events | P50 ms | P95 ms | P99 ms | Max ms | Errors |
|---|---|---:|---:|---:|---:|---:|---:|
| before | fastapi_resnet18 | 3086 | 140.5822 | 171.6784 | 201.4458 | 462.446 | 0 |
| before | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| before | yolo_detection | 137 | 136.8439 | 174.3549 | 306.1107 | 1718.432 | 0 |
| during | fastapi_resnet18 | 467 | 167.7709 | 273.5393 | 781.7349 | 950.5697 | 0 |
| during | fastapi_whisper | 2 | 5799.7609 | 8377.5258 | 8606.6604 | 8663.9441 | 0 |
| during | yolo_detection | 31 | 123.4425 | 156.9111 | 164.334 | 165.0779 | 0 |
| after | fastapi_resnet18 | 3094 | 142.0489 | 170.3055 | 191.6536 | 468.115 | 0 |
| after | fastapi_whisper | 0 | n/a | n/a | n/a | n/a | 0 |
| after | yolo_detection | 152 | 136.9543 | 181.2703 | 187.1359 | 190.4087 | 0 |

## Aggregate Telemetry By Phase

| Phase | Samples | GR3D avg % | CPU avg % | RAM avg MB | GPU temp max C | VDD_IN avg mW |
|---|---:|---:|---:|---:|---:|---:|
| before | 70 | 53.4 | 39.676 | 3364.029 | 46.375 | 7981.771 |
| during | 20 | 53.5 | 39.492 | 3532.4 | 46.406 | 7832.05 |
| after | 70 | 54.714 | 39.488 | 3710.471 | 47.156 | 8016.229 |

## Aggregate Deltas

| Delta | Metric | Value |
|---|---|---:|
| during_minus_before_latency_ms | fastapi_resnet18.p50 | 27.1887 |
| during_minus_before_latency_ms | fastapi_resnet18.p95 | 101.8609 |
| during_minus_before_latency_ms | fastapi_resnet18.p99 | 580.2891 |
| during_minus_before_latency_ms | fastapi_resnet18.max | 488.1237 |
| during_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| during_minus_before_latency_ms | fastapi_whisper.max | n/a |
| during_minus_before_latency_ms | yolo_detection.p50 | -13.4014 |
| during_minus_before_latency_ms | yolo_detection.p95 | -17.4438 |
| during_minus_before_latency_ms | yolo_detection.p99 | -141.7767 |
| during_minus_before_latency_ms | yolo_detection.max | -1553.3541 |
| after_minus_before_latency_ms | fastapi_resnet18.p50 | 1.4667 |
| after_minus_before_latency_ms | fastapi_resnet18.p95 | -1.3729 |
| after_minus_before_latency_ms | fastapi_resnet18.p99 | -9.7922 |
| after_minus_before_latency_ms | fastapi_resnet18.max | 5.669 |
| after_minus_before_latency_ms | fastapi_whisper.p50 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p95 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.p99 | n/a |
| after_minus_before_latency_ms | fastapi_whisper.max | n/a |
| after_minus_before_latency_ms | yolo_detection.p50 | 0.1104 |
| after_minus_before_latency_ms | yolo_detection.p95 | 6.9154 |
| after_minus_before_latency_ms | yolo_detection.p99 | -118.9748 |
| after_minus_before_latency_ms | yolo_detection.max | -1528.0233 |
| during_minus_before_telemetry | ram_used_mb_avg | 168.371 |
| during_minus_before_telemetry | ram_used_mb_max | 0.0 |
| during_minus_before_telemetry | gr3d_freq_pct_avg | 0.1 |
| during_minus_before_telemetry | gr3d_freq_pct_max | 0.0 |
| during_minus_before_telemetry | cpu_busy_pct_avg | -0.184 |
| during_minus_before_telemetry | cpu_busy_pct_max | -6.0 |
| during_minus_before_telemetry | gpu_temp_c_max | 0.031 |
| during_minus_before_telemetry | vdd_in_mw_avg | -149.721 |
| during_minus_before_telemetry | vdd_in_mw_max | -464.0 |
| after_minus_before_telemetry | ram_used_mb_avg | 346.442 |
| after_minus_before_telemetry | ram_used_mb_max | 7.0 |
| after_minus_before_telemetry | gr3d_freq_pct_avg | 1.314 |
| after_minus_before_telemetry | gr3d_freq_pct_max | 1.0 |
| after_minus_before_telemetry | cpu_busy_pct_avg | -0.188 |
| after_minus_before_telemetry | cpu_busy_pct_max | -6.0 |
| after_minus_before_telemetry | gpu_temp_c_max | 0.781 |
| after_minus_before_telemetry | vdd_in_mw_avg | 34.458 |
| after_minus_before_telemetry | vdd_in_mw_max | -704.0 |

## Per-Burst Summary

| Burst | Phase | FastAPI p99 ms | YOLO p99 ms | Whisper max ms | GR3D avg % | CPU avg % |
|---:|---|---:|---:|---:|---:|---:|
| 0 | before | 201.8236 | 798.4731 | n/a | 52.057 | 39.691 |
| 0 | during | 819.4306 | 164.5324 | 8663.9441 | 50.0 | 38.716 |
| 0 | after | 192.9715 | 187.6553 | n/a | 57.171 | 39.409 |
| 1 | before | 196.5908 | 232.06 | n/a | 54.743 | 39.662 |
| 1 | during | 195.9014 | 150.2457 | 2935.5777 | 57.0 | 40.267 |
| 1 | after | 190.3683 | 184.5886 | n/a | 52.257 | 39.567 |

## Boundary

- Latency windows are event-level summaries around Whisper bursts.
- Telemetry windows are compact timeline-bucket summaries, not raw sensor replay.
- Treat spikes and deltas as runtime reliability signals, not deployment capacity proof.
