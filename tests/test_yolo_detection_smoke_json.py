#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    payload = json.loads((repo / "results/inference/yolo_yolov8n_detection_20260516_010734.json").read_text(encoding="utf-8"))
    assert payload["metadata"]["schema_version"] == "yolo-detection-smoke-v1"
    assert payload["metadata"]["tegrastats_log"] == "artifacts/system/tegrastats_yolo_yolov8n_20260516_010734.log"
    result = payload["result"]
    assert result["task"] == "object_detection_smoke"
    assert result["framework"] == "ultralytics"
    assert result["backend"] == "cuda"
    assert result["precision"] == "fp32"
    assert result["model"]["architecture"] == "yolov8n"
    assert result["model"]["path"] == "models/yolov8n.pt"
    assert len(result["model"]["sha256"]) == 64
    assert result["input"]["external_sensor_dependency"] is False
    assert result["input"]["path"] == "[site-packages]/ultralytics/assets/bus.jpg"
    assert result["runtime"]["preprocessing_included"] is True
    assert result["runtime"]["postprocessing_included"] is True
    assert result["latency"]["count"] == result["runtime"]["repeat"]
    assert result["output"]["detection_count"] >= 1
    assert result["output"]["class_counts"].get("bus") == 1
    assert result["interpretation"]["accuracy_claim"] is False
    assert result["interpretation"]["deployment_ready_claim"] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
