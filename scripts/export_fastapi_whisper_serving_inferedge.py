#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_whisper_serving_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_fastapi_whisper_smoke() -> Path:
    matches = sorted(Path("results/inference").glob("fastapi_whisper_speech_server_*.json"))
    if not matches:
        raise FileNotFoundError("no FastAPI Whisper speech server smoke JSON found")
    return matches[-1]


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    serving = result["serving"]
    audio = result["audio"]
    transcription = result["transcription"]
    client = serving["latency_layers"]["client_roundtrip_ms"]
    server = serving["latency_layers"]["server_transcription_ms"]
    try:
        output_text = str(output_dir.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        output_text = str(output_dir)
    lines = [
        "# FastAPI Whisper InferEdge Serving Export Report",
        "",
        "> FastAPI Whisper localhost speech serving smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{output_text}/metadata.json` | Forge/Lab handoff metadata envelope |",
        f"| `{output_text}/result.json` | Lab-compatible audio serving result envelope |",
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
        f"| serving ready | {result['extra']['serving_ready']} |",
        f"| transcription ready | {result['extra']['transcription_ready']} |",
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Endpoint",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Framework | `{serving['framework']}` |",
        f"| ASGI | `{serving['asgi']}` |",
        f"| Endpoint | `{serving['endpoint']}` |",
        f"| Backend | `{result['engine_backend']}` |",
        f"| Precision | `{result['precision']}` |",
        "",
        "## Audio / Transcription",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Audio path | `{audio['path']}` |",
        f"| Audio SHA256 | `{audio['sha256']}` |",
        f"| Duration s | {audio['duration_s']} |",
        f"| Expected text | `{transcription['expected_text']}` |",
        f"| Transcript | `{transcription['text']}` |",
        f"| Expected matched | {transcription['normalized_contains_expected']} |",
        "",
        "## Latency",
        "",
        "| Layer | Mean ms | P95 ms | P99 ms |",
        "|---|---:|---:|---:|",
        f"| Client roundtrip | {client['mean_ms']} | {client['p95_ms']} | {client['p99_ms']} |",
        f"| Server transcription | {server['mean_ms']} | {server['p95_ms']} | {server['p99_ms']} |",
        "",
        "## Notes",
        "",
        "- This is localhost audio serving-layer evidence, not a deployment approval.",
        "- Client roundtrip latency includes local HTTP serialization, FastAPI routing, audio path validation, transcription, and response serialization.",
        "- The exported `result.json` preserves InferEdge-compatible serving top-level fields while keeping audio and transcription details under `audio`, `transcription`, and `serving`.",
        "- The generated speech sample validates plumbing for one license-clear phrase; it is not a broad speech recognition accuracy benchmark.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FastAPI Whisper serving smoke as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--fastapi-whisper-smoke", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    fastapi_whisper_smoke = args.fastapi_whisper_smoke or latest_fastapi_whisper_smoke()
    metadata, result = build_inferedge_whisper_serving_export(fastapi_whisper_smoke, args.output_dir, Path.cwd())
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
