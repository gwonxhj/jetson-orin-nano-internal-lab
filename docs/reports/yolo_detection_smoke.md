# YOLO Object Detection Smoke Report

> YOLOv8n file-image object detection path를 Jetson 내부에서 실행한 optional extension evidence입니다.
> Ultralytics package sample image와 pretrained smoke model을 사용하므로 broad accuracy evidence가 아니라 local detection pipeline evidence입니다.

## Run Information

| Field | Value |
|---|---|
| Date | 2026-05-16T01:07:41+09:00 |
| Hostname | `jetson-orin-nano` |
| Conda env | `yolo_env` |
| Result schema | `yolo-detection-smoke-v1` |
| Tegrastats log | `artifacts/system/tegrastats_yolo_yolov8n_20260516_010734.log` |

## Model / Input

| Field | Value |
|---|---|
| Model | yolov8n.pt |
| Model path | `models/yolov8n.pt` |
| Model sha256 | `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36` |
| Backend | cuda |
| Precision | fp32 |
| Image | `[site-packages]/ultralytics/assets/bus.jpg` |
| Image sha256 | `c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63` |
| Image size | 810x1080 |
| Image source | ultralytics_package_sample_image |

## Latency

| Metric | Value ms |
|---|---:|
| Warmup | 3 runs |
| Repeat | 20 runs |
| Mean | 59.5495 |
| P50 | 61.0896 |
| P95 | 61.3837 |
| P99 | 61.4791 |
| Min | 54.4237 |
| Max | 61.5029 |

## Detection Preview

- Detection count: 6
- Class counts: `{"bus": 1, "person": 4, "stop sign": 1}`

| Class | Confidence | Box xyxy |
|---|---:|---|
| bus | 0.873246 | `[22.839, 231.275, 804.992, 756.84]` |
| person | 0.865758 | `[48.555, 398.551, 245.343, 902.713]` |
| person | 0.852866 | `[669.471, 392.198, 809.72, 877.035]` |
| person | 0.82527 | `[221.511, 405.797, 344.973, 857.538]` |
| person | 0.260886 | `[0.0, 550.52, 63.038, 873.439]` |
| stop sign | 0.25524 | `[0.057, 254.46, 32.559, 324.87]` |

## Boundary

- This is file-image object detection smoke evidence, not production camera validation.
- It does not use external cameras, sensors, microphones, motors, or robot hardware.
- It does not claim broad object detection accuracy or deployment readiness.
- Backend, model hash, image hash, warmup/repeat, confidence threshold, and image size are recorded for reproducibility.
