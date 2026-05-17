# Multi-Workload Runtime Timeline Export

> multi-workload evidence를 workload event + `tegrastats` bucket timeline으로 정리한 보고서입니다.
> 이 timeline은 runtime interaction 분석용 evidence이며 production capacity plan이 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_023351.json` |
| Bucket size | 5.0 s |
| Duration | 120.1017 s |
| Buckets | 25 |
| Workload events | 6351 |
| Tegrastats samples | 128 |

## Workload Totals

| Workload | Events | Success | Errors | Mean ms | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 6058 | 6058 | 0 | 147.3829 | 181.4991 | 268.4134 | 950.5697 |
| fastapi_whisper | 2 | 2 | 0 | 5799.7609 | 8377.5258 | 8606.6604 | 8663.9441 |
| yolo_detection | 291 | 291 | 0 | 145.8958 | 177.8141 | 187.8364 | 1718.432 |

## Telemetry Summary

| Metric | Value |
|---|---:|
| RAM used avg MB | 3442.766 |
| RAM used max MB | 3747.0 |
| GR3D avg % | 50.758 |
| GR3D max % | 99.0 |
| CPU busy avg % | 38.367 |
| CPU busy max % | 100.0 |
| GPU temp max C | 47.156 |
| VDD_IN avg mW | 7822.188 |
| VDD_IN max mW | 9050.0 |

## Whisper Bursts

| Burst | Start s | End s | Duration ms | OK |
|---:|---:|---:|---:|---|
| 0 | 30.0391 | 38.703 | 8663.9441 | True |
| 1 | 83.7481 | 86.6837 | 2935.5777 | True |

## Top Latency Buckets

| Rank | Workload | Bucket | Max ms |
|---:|---|---:|---:|
| 1 | fastapi_whisper | 6 | 8663.9441 |
| 2 | fastapi_whisper | 16 | 2935.5777 |
| 3 | yolo_detection | 0 | 1718.432 |
| 4 | fastapi_resnet18 | 7 | 950.5697 |
| 5 | fastapi_resnet18 | 0 | 836.4011 |
| 6 | fastapi_resnet18 | 21 | 468.115 |
| 7 | fastapi_resnet18 | 11 | 462.446 |
| 8 | fastapi_resnet18 | 12 | 450.3668 |
| 9 | fastapi_resnet18 | 5 | 416.1436 |
| 10 | yolo_detection | 15 | 374.1414 |

## Boundary

- This is compact runtime interaction evidence, not a production load test.
- Buckets summarize workload and telemetry behavior; raw logs remain the source of truth.
- Use this artifact for timeline alignment, p99/burst-window analysis, and future degradation signal review.
