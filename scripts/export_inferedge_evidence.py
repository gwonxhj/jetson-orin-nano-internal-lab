#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_runtime_compare() -> Path:
    matches = sorted(Path("results/runtime_compare").glob("resnet18_pytorch_cuda_fp32_vs_tensorrt_fp16_*.json"))
    if not matches:
        raise FileNotFoundError("no runtime comparison JSON found")
    return matches[-1]



def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    comparison = result["comparison"]
    lines = [
        "# InferEdge Export Report",
        "",
        "> Runtime comparison evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{output_dir / 'metadata.json'}` | Forge/Lab handoff metadata envelope |",
        f"| `{output_dir / 'result.json'}` | Lab-compatible Runtime result envelope with comparison evidence |",
        "",
        "## Compatibility",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| metadata schema | `{metadata['schema_version']}` |",
        f"| result schema | `{result['schema_version']}` |",
        f"| compare key | `{result['compare_key']}` |",
        f"| backend key | `{result['backend_key']}` |",
        f"| handoff ready | {metadata['handoff']['ready']} |",
        f"| compare ready | {result['extra']['compare_ready']} |",
        f"| verdict | `{comparison['verdict']}` |",
        "",
        "## Runtime Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| TensorRT mean ms | {result['mean_ms']} |",
        f"| TensorRT p95 ms | {result['p95_ms']} |",
        f"| TensorRT p99 ms | {result['p99_ms']} |",
        f"| TensorRT throughput qps | {result['fps_value']} |",
        f"| PyTorch/TensorRT mean ratio | {comparison['ratios']['mean_latency_pytorch_over_tensorrt']}x |",
        "",
        "## Notes",
        "",
        "- This is runtime comparison evidence, not a deployment approval.",
        "- PyTorch CUDA FP32 and TensorRT FP16 differ in precision/runtime, so the comparison is not a direct regression verdict.",
        "- The exported `result.json` keeps Lab-compatible top-level fields while preserving comparison details under `comparison`.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description="Export runtime comparison as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--runtime-compare", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    runtime_compare = args.runtime_compare or latest_runtime_compare()
    metadata, result = build_inferedge_export(runtime_compare, args.output_dir, Path.cwd())
    validate_inferedge_result(result)

    result_path = args.output_dir / "result.json"
    metadata_path = args.output_dir / "metadata.json"
    write_json(result_path, result)
    for artifact in metadata["artifacts"]:
        if artifact["role"] == "runtime_result":
            artifact["sha256"] = sha256_file(result_path)
    validate_inferedge_metadata(metadata)
    write_json(metadata_path, metadata)

    # Re-read to ensure the serialized files still satisfy the schema helpers.
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
