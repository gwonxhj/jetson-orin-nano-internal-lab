# FastAPI ResNet18 Concurrency Smoke Report

> ResNet18 synthetic inference endpoint에 대해 localhost 동시 요청 smoke를 기록한 보고서입니다.
> 이 결과는 짧은 concurrency path evidence이며 deployment-ready, load test, soak test evidence가 아닙니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-14T23:32:55+09:00 |
| Hostname | `jetson-orin-nano` |
| Base URL | `http://127.0.0.1:18082` |
| Endpoint | `/v1/infer/resnet18/synthetic` |
| Server log | `artifacts/system/fastapi_concurrency_server_20260514_233246.log` |
| Tegrastats log | `artifacts/system/tegrastats_fastapi_concurrency_20260514_233246.log` |

## Request

| Field | Value |
|---|---|
| Backend | cuda |
| Precision | fp32 |
| Input shape | [1, 3, 224, 224] |
| Warmup | 2 |
| Requests per level | 8 |

## Concurrency Results

| Concurrency | Requests | Success | Errors | Wall ms | Throughput rps | Client mean ms | Client p95 ms | Server mean ms | Server p95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 8 | 0 | 221.3767 | 36.1375 | 27.1314 | 29.3856 | 17.6186 | 18.761 |
| 2 | 8 | 8 | 0 | 191.9466 | 41.6782 | 46.7295 | 75.3383 | 31.3639 | 56.3225 |
| 4 | 8 | 8 | 0 | 155.7489 | 51.3647 | 66.0945 | 115.9279 | 47.2236 | 93.3573 |

## Interpretation

- This is localhost concurrency smoke, not deployment approval.
- Throughput is measured from client-side wall time for each concurrency level.
- Server inference timing is still measured inside the handler around the PyTorch model call.
- Compare this evidence only as a serving-layer system comparison, not as a direct regression against TensorRT or ONNX Runtime.
