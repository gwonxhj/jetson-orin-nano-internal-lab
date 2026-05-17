# Multi-Workload Degradation Signal Report

> Opt-in overload/concurrency scenario에서 관찰된 bounded runtime degradation signal을 정리한 보고서입니다.
> 이 보고서는 reliability signal evidence이며 production stress test, capacity plan, deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_023351.json` |
| Timeline JSON | `results/runtime_compare/multi_workload_degradation_timeline_20260518_023351.json` |
| Burst-window JSON | `results/runtime_compare/multi_workload_degradation_burst_windows_20260518_023351.json` |
| Duration | 120.1017 s |
| Degradation signal observed | True |

## Opt-In Overload Config

| Field | Value |
|---|---:|
| fastapi_concurrency | 8 |
| fastapi_interval_s | 0.01 |
| whisper_repeat | 2 |
| whisper_interval_s | 45.0 |
| yolo_interval_s | 0.25 |

## Event Summary

| Workload | Events | Success | Errors | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 6058 | 6058 | 0 | 181.4991 | 268.4134 | 950.5697 |
| fastapi_whisper | 2 | 2 | 0 | 8377.5258 | 8606.6604 | 8663.9441 |
| yolo_detection | 291 | 291 | 0 | 177.8141 | 187.8364 | 1718.432 |

## Signals

| Signal | Value |
|---|---:|
| FastAPI p99 spike | True |
| FastAPI max spike | True |
| Resource pressure delta | True |
| Runtime errors observed | False |
| During-before FastAPI p99 delta ms | 580.2891 |
| During-before FastAPI max delta ms | 488.1237 |

## Telemetry Delta During Minus Before

| Metric | Delta |
|---|---:|
| cpu_busy_pct_avg | -0.184 |
| cpu_busy_pct_max | -6.0 |
| gpu_temp_c_max | 0.031 |
| gr3d_freq_pct_avg | 0.1 |
| gr3d_freq_pct_max | 0.0 |
| ram_used_mb_avg | 168.371 |
| ram_used_mb_max | 0.0 |
| vdd_in_mw_avg | -149.721 |
| vdd_in_mw_max | -464.0 |

## Boundary

- This is an opt-in bounded overload scenario, not the default benchmark path.
- Signals are preserved even when no request errors occur; latency and resource pressure are reliability signals too.
- Do not use this as a production capacity or deployment-ready claim.
