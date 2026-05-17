# Multi-Workload Runtime Timeline Export

> 30-minute sustained multi-workload evidence를 workload event + `tegrastats` bucket timeline으로 정리한 보고서입니다.
> 이 timeline은 runtime interaction 분석용 evidence이며 production capacity plan이 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_sustained_20260518_002910.json` |
| Bucket size | 10.0 s |
| Duration | 1800.0892 s |
| Buckets | 181 |
| Workload events | 35935 |
| Tegrastats samples | 1799 |

## Workload Totals

| Workload | Events | Success | Errors | Mean ms | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| fastapi_resnet18 | 34324 | 34324 | 0 | 54.2977 | 68.0591 | 84.1843 | 785.0608 |
| fastapi_whisper | 5 | 5 | 0 | 1313.5877 | 3521.1574 | 4099.046 | 4243.5182 |
| yolo_detection | 1606 | 1606 | 0 | 117.7534 | 144.4643 | 148.0224 | 1341.9493 |

## Telemetry Summary

| Metric | Value |
|---|---:|
| RAM used avg MB | 3461.086 |
| RAM used max MB | 3844.0 |
| GR3D avg % | 34.513 |
| GR3D max % | 99.0 |
| CPU busy avg % | 12.609 |
| CPU busy max % | 100.0 |
| GPU temp max C | 45.468 |
| VDD_IN avg mW | 5609.613 |
| VDD_IN max mW | 6690.0 |

## Whisper Bursts

| Burst | Start s | End s | Duration ms | OK |
|---:|---:|---:|---:|---|
| 0 | 300.0338 | 304.2774 | 4243.5182 | True |
| 1 | 604.3767 | 604.9748 | 598.1001 | True |
| 2 | 905.0036 | 905.543 | 539.4265 | True |
| 3 | 1205.6319 | 1206.2636 | 631.7141 | True |
| 4 | 1506.2768 | 1506.832 | 555.1795 | True |

## Top Latency Buckets

| Rank | Workload | Bucket | Max ms |
|---:|---|---:|---:|
| 1 | fastapi_whisper | 30 | 4243.5182 |
| 2 | yolo_detection | 0 | 1341.9493 |
| 3 | fastapi_resnet18 | 30 | 785.0608 |
| 4 | fastapi_resnet18 | 0 | 678.3729 |
| 5 | fastapi_whisper | 120 | 631.7141 |
| 6 | fastapi_whisper | 60 | 598.1001 |
| 7 | fastapi_whisper | 150 | 555.1795 |
| 8 | fastapi_whisper | 90 | 539.4265 |
| 9 | fastapi_resnet18 | 107 | 357.5047 |
| 10 | yolo_detection | 162 | 347.2609 |

## Boundary

- This is compact runtime interaction evidence, not a production load test.
- Buckets summarize workload and telemetry behavior; raw logs remain the source of truth.
- Use this artifact for timeline alignment, p99/burst-window analysis, and future degradation signal review.
