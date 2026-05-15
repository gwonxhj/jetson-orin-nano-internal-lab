#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_soak_burst_serving_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_soak_burst() -> Path:
    matches = sorted(Path("results/inference").glob("fastapi_resnet18_soak_burst_*.json"))
    if not matches:
        raise FileNotFoundError("no FastAPI ResNet18 soak/burst JSON found")
    return matches[-1]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    serving = result["serving"]
    soak = serving["soak"]
    client = serving["latency_layers"]["client_roundtrip_ms"]
    server = serving["latency_layers"]["server_inference_ms"]
    lines = [
        "# FastAPI Soak/Burst InferEdge Export Report",
        "",
        "> FastAPI ResNet18 localhost soak/burst evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{_display_path(output_dir / 'metadata.json')}` | Forge/Lab handoff metadata envelope |",
        f"| `{_display_path(output_dir / 'result.json')}` | Lab-compatible serving result envelope |",
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
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Soak Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Soak duration s | {soak['target_duration_s']} |",
        f"| Soak concurrency | {soak['concurrency']} |",
        f"| Requests | {soak['requests']} |",
        f"| Success | {soak['success_count']} |",
        f"| Errors | {soak['error_count']} |",
        f"| Throughput rps | {soak['throughput_rps']} |",
        "",
        "## Latency",
        "",
        "| Layer | Mean ms | P95 ms | P99 ms |",
        "|---|---:|---:|---:|",
        f"| Client roundtrip | {client['mean_ms']} | {client['p95_ms']} | {client['p99_ms']} |",
        f"| Server inference | {server['mean_ms']} | {server['p95_ms']} | {server['p99_ms']} |",
        "",
        "## Burst Summary",
        "",
        "| Concurrency | Requests | Success | Errors | Throughput rps | Client p95 ms | Server p95 ms |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in serving["burst"]:
        lines.append(
            f"| {row['concurrency']} | {row['requests']} | {row['success_count']} | {row['error_count']} | "
            f"{row['throughput_rps']} | {row['client_roundtrip_ms']['p95_ms']} | {row['server_inference_ms']['p95_ms']} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "- This is localhost serving-layer evidence, not deployment approval.",
        "- The export keeps soak and burst sections under `serving` while using soak client roundtrip latency as the top-level serving summary.",
        "- Client roundtrip and server handler inference remain separate so API overhead is not collapsed into model latency.",
        "- This evidence does not claim capacity planning or production load-test coverage.",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FastAPI soak/burst evidence as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--soak-burst", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    soak_burst = args.soak_burst or latest_soak_burst()
    metadata, result = build_inferedge_soak_burst_serving_export(soak_burst, args.output_dir, Path.cwd())
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
