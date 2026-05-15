#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_yolo_detection_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_yolo_detection_smoke() -> Path:
    matches = sorted(Path("results/inference").glob("yolo_*_detection_*.json"))
    if not matches:
        raise FileNotFoundError("no YOLO detection smoke JSON found")
    return matches[-1]


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    detection = result["object_detection"]
    latency = result["latency_ms"]
    try:
        output_text = str(output_dir.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        output_text = str(output_dir)
    lines = [
        "# YOLO Detection InferEdge Export Report",
        "",
        "> YOLOv8n file-image object detection smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{output_text}/metadata.json` | Forge/Lab handoff metadata envelope |",
        f"| `{output_text}/result.json` | Lab-compatible object detection result envelope |",
        "",
        "## Compatibility",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| metadata schema | `{metadata['schema_version']}` |",
        f"| result schema | `{result['schema_version']}` |",
        f"| runtime role | `{result['runtime_role']}` |",
        f"| compare key | `{result['compare_key']}` |",
        f"| backend key | `{result['backend_key']}` |",
        f"| handoff ready | {metadata['handoff']['ready']} |",
        f"| object detection ready | {result['extra']['object_detection_ready']} |",
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Detection Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | `{detection['model_name']}` |",
        f"| Model SHA256 | `{detection['model_sha256']}` |",
        f"| Input | `{detection['input_path']}` |",
        f"| Input source | `{detection['input_source']}` |",
        f"| Input SHA256 | `{detection['input_sha256']}` |",
        f"| Input shape | `{detection['input_height']}x{detection['input_width']}` |",
        f"| Detection count | {detection['detection_count']} |",
        f"| Class counts | `{detection['class_counts']}` |",
        f"| Mean ms | {latency['mean']} |",
        f"| P95 ms | {latency['p95']} |",
        f"| FPS | {result['fps']} |",
        "",
        "## Notes",
        "",
        "- This is file-image object detection path evidence, not a broad detection accuracy benchmark.",
        "- The sample input comes from the Ultralytics package, so no external camera, sensor, or robot part is required.",
        "- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export YOLO detection smoke as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--yolo-smoke", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    yolo_smoke = args.yolo_smoke or latest_yolo_detection_smoke()
    metadata, result = build_inferedge_yolo_detection_export(yolo_smoke, args.output_dir, Path.cwd())
    validate_inferedge_result(result)

    result_path = args.output_dir / "result.json"
    metadata_path = args.output_dir / "metadata.json"
    write_json(result_path, result)
    for artifact in metadata["artifacts"]:
        if artifact["role"] == "runtime_result":
            artifact["sha256"] = sha256_file(result_path)
    validate_inferedge_metadata(metadata)
    write_json(metadata_path, metadata)

    validate_inferedge_result(read_json(result_path))
    validate_inferedge_metadata(read_json(metadata_path))
    if args.report is not None:
        write_report(args.output_dir, args.report)
        print(args.report)
    print(metadata_path)
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
