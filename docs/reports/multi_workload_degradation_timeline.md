# Multi-Workload Runtime Timeline Export

> multi-workload evidence를 workload event + `tegrastats` bucket timeline으로 정리한 보고서입니다.
> 이 timeline은 runtime interaction 분석용 evidence이며 production capacity plan이 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_013625.json` |
| Bucket size | 5.0 s |
| Duration | 300.08 s |
| Buckets | 61 |
| Workload events | 16226 |
| Tegrastats samples | 309 |

## Workload Totals

| Workload | Events | Success | Errors | Mean ms | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 15472 | 15472 | 0 | 144.1454 | 173.0672 | 226.3634 | 883.8447 |
| fastapi_whisper | 3 | 3 | 0 | 4850.8652 | 8787.4625 | 9307.4887 | 9437.4952 |
| yolo_detection | 751 | 751 | 0 | 142.3628 | 173.2865 | 184.0366 | 1690.4935 |

## Telemetry Summary

| Metric | Value |
|---|---:|
| RAM used avg MB | 3433.589 |
| RAM used max MB | 3671.0 |
| GR3D avg % | 52.612 |
| GR3D max % | 99.0 |
| CPU busy avg % | 39.083 |
| CPU busy max % | 100.0 |
| GPU temp max C | 49.75 |
| VDD_IN avg mW | 7978.372 |
| VDD_IN max mW | 9050.0 |

## Whisper Bursts

| Burst | Start s | End s | Duration ms | OK |
|---:|---:|---:|---:|---|
| 0 | 60.0481 | 69.4856 | 9437.4952 | True |
| 1 | 129.5435 | 132.4806 | 2937.1685 | True |
| 2 | 192.54 | 194.7179 | 2177.9319 | True |

## Top Latency Buckets

| Rank | Workload | Bucket | Max ms |
|---:|---|---:|---:|
| 1 | fastapi_whisper | 12 | 9437.4952 |
| 2 | fastapi_whisper | 25 | 2937.1685 |
| 3 | fastapi_whisper | 38 | 2177.9319 |
| 4 | yolo_detection | 0 | 1690.4935 |
| 5 | fastapi_resnet18 | 13 | 883.8447 |
| 6 | fastapi_resnet18 | 0 | 825.2628 |
| 7 | fastapi_resnet18 | 12 | 534.4199 |
| 8 | fastapi_resnet18 | 46 | 506.1573 |
| 9 | fastapi_resnet18 | 21 | 494.8059 |
| 10 | fastapi_resnet18 | 29 | 478.9289 |

## Boundary

- This is compact runtime interaction evidence, not a production load test.
- Buckets summarize workload and telemetry behavior; raw logs remain the source of truth.
- Use this artifact for timeline alignment, p99/burst-window analysis, and future degradation signal review.
