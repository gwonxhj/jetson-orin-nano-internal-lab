# Multi-Workload Serving Observability Report

> FastAPI server/client queue, backlog, failed-request proxy를 multi-workload runtime evidence에서 분리한 보고서입니다.
> 이 보고서는 localhost serving reliability evidence이며 production queue-depth telemetry나 deployment-ready proof가 아닙니다.

## Source

| Field | Value |
|---|---|
| Source JSON | `results/runtime_compare/multi_workload_degradation_20260518_023351.json` |
| Duration | 120.1017 s |
| Target duration | 120.0 s |

## Request Counts

| Signal | Value |
|---|---:|
| client_completed_count | 6060 |
| client_failed_count | 0 |
| server_total_requests | 6063 |
| server_failed_requests | 0 |
| resnet_endpoint_count | 6058 |
| resnet_endpoint_failed_count | 0 |
| whisper_endpoint_count | 2 |
| whisper_endpoint_failed_count | 0 |

## Queue / Backlog Proxy Signals

| Signal | Value |
|---|---:|
| max_client_outstanding | 8 |
| max_server_inflight_requests | 9 |
| client_failed_requests | 0 |
| server_failed_requests | 0 |
| dropped_request_count_proxy | 0 |
| backlog_proxy_observed | True |
| failed_or_dropped_observed | False |

## Workload Error Summary

| Workload | Events | Success | Errors |
|---|---:|---:|---:|
| fastapi_resnet18 | 6058 | 6058 | 0 |
| fastapi_whisper | 2 | 2 | 0 |
| yolo_detection | 291 | 291 | 0 |

## Boundary

- In-process `max_inflight_requests` and client worker outstanding counts are backlog proxies.
- Failed requests are preserved as dropped-request proxy evidence when explicit queue drops are not available.
- This report supports runtime reliability interpretation, not production capacity planning.
