#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_audio_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_whisper_speech_smoke() -> Path:
    matches = sorted(Path("results/inference").glob("whisper_*_speech_transcription_*.json"))
    if not matches:
        raise FileNotFoundError("no Whisper speech transcription smoke JSON found")
    return matches[-1]


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    audio = result["audio"]
    transcription = result["transcription"]
    latency = result["latency_ms"]
    try:
        output_text = str(output_dir.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        output_text = str(output_dir)
    lines = [
        "# Whisper InferEdge Export Report",
        "",
        "> Whisper speech transcription smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{output_text}/metadata.json` | Forge/Lab handoff metadata envelope |",
        f"| `{output_text}/result.json` | Lab-compatible audio transcription result envelope |",
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
        f"| transcription ready | {result['extra']['transcription_ready']} |",
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Audio Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Audio path | `{audio['path']}` |",
        f"| Audio source | `{audio['source']}` |",
        f"| Audio SHA256 | `{audio['sha256']}` |",
        f"| Duration s | {audio['duration_s']} |",
        f"| Sample rate Hz | {audio['sample_rate_hz']} |",
        "",
        "## Transcription Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Expected text | `{transcription['expected_text']}` |",
        f"| Transcript | `{transcription['text']}` |",
        f"| Expected matched | {transcription['normalized_contains_expected']} |",
        f"| Mean ms | {latency['mean']} |",
        f"| P95 ms | {latency['p95']} |",
        f"| Real-time factor | {result['comparison']['ratios']['real_time_factor']} |",
        "",
        "## Notes",
        "",
        "- This is a license-clear generated speech transcription smoke, not a broad accuracy benchmark.",
        "- The exported `result.json` keeps InferEdge-compatible top-level fields while preserving audio details under `audio` and `transcription`.",
        "- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Whisper speech smoke as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--whisper-smoke", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    whisper_smoke = args.whisper_smoke or latest_whisper_speech_smoke()
    metadata, result = build_inferedge_audio_export(whisper_smoke, args.output_dir, Path.cwd())
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
