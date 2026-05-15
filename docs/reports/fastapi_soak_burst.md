# FastAPI ResNet18 Soak/Burst Report

> ResNet18 synthetic inference endpoint에 대해 localhost longer soak와 burst 요청을 함께 기록한 후속 보고서입니다.
> 이 결과는 serving-layer realism을 조금 높인 evidence이며 deployment-ready, capacity plan, production load test가 아닙니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-15T22:29:51+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18083` |
| Endpoint | `/v1/infer/resnet18/synthetic` |
| Server log | `artifacts/system/fastapi_soak_burst_server_20260515_222841.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_soak_burst_20260515_222841.log` |

## Request

| Field | Value |
|---|---|
| Backend | cuda |
| Precision | fp32 |
| Input shape | [1, 3, 224, 224] |
| Warmup | 5 |
| Soak duration | 60.0 s |
| Soak concurrency | 2 |
| Burst levels | [1, 2, 4, 8] |
| Burst requests per level | 16 |

## Soak Result

| Concurrency | Target s | Requests | Success | Errors | Wall ms | Throughput rps | Client mean ms | Client p95 ms | Server mean ms | Server p95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 60.0 | 2776 | 2776 | 0 | 60030.5569 | 46.2431 | 42.0217 | 43.7574 | 26.2387 | 26.8632 |

## Burst Results

| Concurrency | Requests | Success | Errors | Wall ms | Throughput rps | Client mean ms | Client p95 ms | Server mean ms | Server p95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 16 | 0 | 431.547 | 37.0759 | 26.4483 | 26.8395 | 17.347 | 17.596 |
| 2 | 16 | 16 | 0 | 341.5183 | 46.8496 | 41.2444 | 44.6023 | 26.3351 | 27.6746 |
| 4 | 16 | 16 | 0 | 285.7606 | 55.9909 | 67.7012 | 134.1225 | 49.708 | 113.6965 |
| 8 | 16 | 16 | 0 | 298.3035 | 53.6367 | 130.7437 | 234.0573 | 99.1259 | 193.3753 |

## Interpretation

- This is localhost serving evidence, not deployment approval.
- Soak checks a longer repeated request path while `tegrastats` records a side telemetry log.
- Burst checks short concurrency levels and should be interpreted as serving-layer system comparison only.
- Client roundtrip and server handler inference are intentionally kept separate.
- This evidence does not cover remote clients, TLS, auth, process supervision, restart policy, or production observability.
