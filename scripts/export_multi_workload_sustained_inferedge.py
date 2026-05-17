#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_multi_workload_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_multi_workload() -> Path:
    matches = sorted(Path("results/runtime_compare").glob("multi_workload_sustained_*.json"))
    if not matches:
        raise FileNotFoundError("no multi-workload sustained JSON found under results/runtime_compare")
    return matches[-1]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def _value(summary: dict[str, object], key: str) -> object:
    return summary.get(key, "n/a")


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    interaction = result["workload_interaction"]
    summary = interaction["summary_by_workload"]
    window = interaction["interaction"].get("whisper_window_s", {})
    ratios = result["comparison"]["ratios"]
    lines = [
        "# Multi-Workload InferEdge Export Report",
        "",
        "> YOLO detection loop, FastAPI ResNet18 concurrent requests, and FastAPI Whisper burst evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "> 이 export는 runtime interaction / reliability signal handoff이며 production stress test나 deployment-ready proof가 아닙니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{_display_path(output_dir / 'metadata.json')}` | Forge/Lab handoff metadata envelope |",
        f"| `{_display_path(output_dir / 'result.json')}` | Lab-compatible multi-workload runtime result envelope |",
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
        f"| runtime reliability ready | {result['extra']['runtime_reliability_ready']} |",
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Workload Summary",
        "",
        "| Workload | Events | Success | Errors | Mean ms | P95 ms | Max ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for workload, item in summary.items():
        latency = item["latency_ms"]
        lines.append(
            f"| {workload} | {item['event_count']} | {item['success_count']} | {item['error_count']} | "
            f"{_value(latency, 'mean_ms')} | {_value(latency, 'p95_ms')} | {_value(latency, 'max_ms')} |"
        )
    lines.extend([
        "",
        "## Interaction Window",
        "",
        f"- Whisper window: {window.get('start', 'n/a')}s -> {window.get('end', 'n/a')}s",
        f"- FastAPI during/after p95 ratio: `{ratios.get('fastapi_during_over_after_p95')}`",
        f"- YOLO during/after p95 ratio: `{ratios.get('yolo_during_over_after_p95')}`",
        f"- Total success events/sec: `{ratios.get('total_success_events_per_second')}`",
        "",
        "## Evidence Paths",
        "",
        f"- Source result: `{interaction['source_json']}`",
        f"- Server log: `{interaction['server_log_path']}`",
        f"- Tegrastats log: `{interaction['tegrastats_log_path']}`",
        "",
        "## Notes",
        "",
        "- This is multi-workload runtime interaction evidence, not a direct single-model regression comparison.",
        "- Latency spikes and contention windows are preserved as runtime reliability signals.",
        "- The scenario uses local file/audio/synthetic inputs and does not rely on external cameras, sensors, microphones, motors, or robot hardware.",
        "- The top-level latency summary uses FastAPI ResNet18 client request latency so the handoff remains comparable to serving behavior evidence; detailed YOLO/Whisper latency remains under `workload_interaction`.",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export multi-workload sustained evidence as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--multi-workload", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    source = args.multi_workload or latest_multi_workload()
    metadata, result = build_inferedge_multi_workload_export(source, args.output_dir, Path.cwd())
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
