# FastAPI Serving Boundary Notes

> FastAPI localhost smoke가 증명하는 것과 증명하지 않는 것을 분리해, serving latency evidence가 deployment-ready 주장으로 과해석되지 않게 하는 boundary note입니다.

## What This Evidence Proves

| Claim | Supported by | Notes |
|---|---|---|
| FastAPI app can start on Jetson | `/health`, server log | `uvicorn` starts locally and serves requests on `127.0.0.1:18080`. |
| ResNet18 model path is wired into the API | `/v1/models`, `/v1/infer/resnet18/synthetic` | Same random seeded model hash is exposed through the API response. |
| PyTorch CUDA inference works behind the API | `result.backend`, `result.result.inference_ms` | Server-side timing is measured inside the FastAPI handler around the PyTorch model call. |
| Local HTTP roundtrip can be measured | `client_roundtrip_ms` | Includes request validation, local serialization, routing, tensor generation, inference, and response serialization. |
| Serving output can be exported as evidence | `results/inferedge/resnet18_fastapi_serving_*/result.json` | InferEdge-compatible serving result preserves endpoint, request shape, latency layers, and Jetson telemetry. |

## What This Evidence Does Not Prove

| Non-claim | Why not |
|---|---|
| It is deployment-ready | There is no concurrent load test, soak test, network exposure test, auth, TLS, process supervision, or restart policy validation. |
| It is production-secure | The server is bound to localhost for smoke evidence and does not validate production security controls. |
| It has application accuracy | The model uses random seeded weights and synthetic input; outputs are only path smoke evidence. |
| It generalizes to camera or sensor input | This project intentionally avoids external camera, sensor, motor, or robot dependencies. |
| It is a direct regression against TensorRT | FastAPI/PyTorch CUDA FP32, ONNX Runtime providers, and native TensorRT FP16 measure different runtime layers and precision paths. |
| It represents network latency | The current measurement uses localhost only; remote clients, Wi-Fi, Ethernet, proxies, and serialization formats are not covered. |

## Latency Boundaries

| Layer | Current evidence | Meaning |
|---|---|---|
| Native TensorRT | `results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json` | Engine-level `trtexec` path, not API serving. |
| ONNX Runtime providers | `results/inference/onnxruntime_*` | Provider/session runtime path, not HTTP serving. |
| PyTorch CUDA smoke | `results/inference/pytorch_resnet18_20260513_125245.json` | Direct model call path without FastAPI. |
| FastAPI server inference | `serving.latency_layers.server_inference_ms` | PyTorch model call measured inside the handler. |
| FastAPI client roundtrip | top-level `latency_ms` in serving `result.json` | Localhost request/response path plus server work. |

## Interpretation Rules

- Treat localhost serving smoke as **API path evidence**, not deployment approval.
- Compare FastAPI client roundtrip to direct model runtimes only as a layered system comparison.
- Keep backend, precision, input shape, warmup/repeat, and power mode attached to every latency number.
- Preserve `serving.latency_layers` when exporting evidence so client roundtrip and server inference are not collapsed into one ambiguous number.
- If this server is later exposed beyond localhost, create a new evidence row for network, security, concurrency, and process supervision conditions.

## Evidence Links

| Evidence | Path |
|---|---|
| API usage report | `docs/reports/fastapi_api_usage.md` |
| Server smoke report | `docs/reports/fastapi_resnet18_server_smoke.md` |
| Serving InferEdge export report | `docs/reports/fastapi_inferedge_export.md` |
| Serving result JSON | `results/inferedge/resnet18_fastapi_serving_20260514_142053/result.json` |
