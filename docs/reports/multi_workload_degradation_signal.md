# Multi-Workload Degradation Signal Report

> Opt-in overload/concurrency scenario에서 관찰된 bounded runtime degradation signal을 정리한 보고서입니다.
> 이 보고서는 reliability signal evidence이며 production stress test, capacity plan, deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_013625.json` |
| Timeline JSON | `results/runtime_compare/multi_workload_degradation_timeline_20260518_013625.json` |
| Burst-window JSON | `results/runtime_compare/multi_workload_degradation_burst_windows_20260518_013625.json` |
| Duration | 300.08 s |
| Degradation signal observed | True |

## Opt-In Overload Config

| Field | Value |
|---|---:|
| fastapi_concurrency | 8 |
| fastapi_interval_s | 0.01 |
| whisper_repeat | 3 |
| whisper_interval_s | 60.0 |
| yolo_interval_s | 0.25 |

## Event Summary

| Workload | Events | Success | Errors | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 15472 | 15472 | 0 | 173.0672 | 226.3634 | 883.8447 |
| fastapi_whisper | 3 | 3 | 0 | 8787.4625 | 9307.4887 | 9437.4952 |
| yolo_detection | 751 | 751 | 0 | 173.2865 | 184.0366 | 1690.4935 |

## Signals

| Signal | Value |
|---|---:|
| FastAPI p99 spike | True |
| FastAPI max spike | True |
| Resource pressure delta | True |
| Runtime errors observed | False |
| During-before FastAPI p99 delta ms | 578.9529 |
| During-before FastAPI max delta ms | 389.0388 |

## Telemetry Delta During Minus Before

| Metric | Delta |
|---|---:|
| cpu_busy_pct_avg | 0.007 |
| cpu_busy_pct_max | 0.0 |
| gpu_temp_c_max | -0.281 |
| gr3d_freq_pct_avg | 1.743 |
| gr3d_freq_pct_max | 1.0 |
| ram_used_mb_avg | 84.282 |
| ram_used_mb_max | 0.0 |
| vdd_in_mw_avg | -200.52 |
| vdd_in_mw_max | 0.0 |

## Boundary

- This is an opt-in bounded overload scenario, not the default benchmark path.
- Signals are preserved even when no request errors occur; latency and resource pressure are reliability signals too.
- Do not use this as a production capacity or deployment-ready claim.
