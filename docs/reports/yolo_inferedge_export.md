# YOLO Detection InferEdge Export Report

> YOLOv8n file-image object detection smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.

## Exported Files

| File | Purpose |
|---|---|
| `results/inferedge/yolo_yolov8n_detection_20260516_010734/metadata.json` | Forge/Lab handoff metadata envelope |
| `results/inferedge/yolo_yolov8n_detection_20260516_010734/result.json` | Lab-compatible object detection result envelope |

## Compatibility

| Field | Value |
|---|---|
| metadata schema | `0.1.0` |
| result schema | `inferedge-runtime-result-v1` |
| runtime role | `object-detection-result` |
| compare key | `yolov8n__object_detection__cuda__imgsz640__conf0p25__fp32` |
| backend key | `ultralytics_cuda__jetson` |
| handoff ready | True |
| object detection ready | True |
| verdict | `object_detection_smoke_not_accuracy_benchmark` |

## Detection Summary

| Field | Value |
|---|---|
| Model | `yolov8n.pt` |
| Model SHA256 | `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36` |
| Input | `[site-packages]/ultralytics/assets/bus.jpg` |
| Input source | `ultralytics_package_sample_image` |
| Input SHA256 | `c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63` |
| Input shape | `1080x810` |
| Detection count | 6 |
| Class counts | `{'bus': 1, 'person': 4, 'stop sign': 1}` |
| Mean ms | 59.5495 |
| P95 ms | 61.3837 |
| FPS | 16.7928 |

## Notes

- This is file-image object detection path evidence, not a broad detection accuracy benchmark.
- The sample input comes from the Ultralytics package, so no external camera, sensor, or robot part is required.
- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.
