#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (
    build_inferedge_llm_export,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
    write_json,
)


def latest_llm_smoke() -> Path:
    matches = sorted(Path("results/llm").glob("llm_*_text_generation_*.json"))
    if not matches:
        raise FileNotFoundError("no LLM text-generation smoke JSON found")
    return matches[-1]


def write_report(output_dir: Path, report_path: Path) -> None:
    metadata = read_json(output_dir / "metadata.json")
    result = read_json(output_dir / "result.json")
    text_generation = result["text_generation"]
    latency = result["latency_ms"]
    try:
        output_text = str(output_dir.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        output_text = str(output_dir)
    lines = [
        "# LLM InferEdge Export Report",
        "",
        "> Local LLM text-generation smoke evidence를 InferEdge-compatible `metadata.json` / `result.json` 쌍으로 변환한 기록입니다.",
        "",
        "## Exported Files",
        "",
        "| File | Purpose |",
        "|---|---|",
        f"| `{output_text}/metadata.json` | Forge/Lab handoff metadata envelope |",
        f"| `{output_text}/result.json` | Lab-compatible text-generation result envelope |",
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
        f"| text generation ready | {result['extra']['text_generation_ready']} |",
        f"| verdict | `{result['comparison']['verdict']}` |",
        "",
        "## Runtime Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | `{result['model_name']}` |",
        f"| Engine | `{result['engine_backend']}` |",
        f"| Device | `{result['run_config']['device'] if 'device' in result['run_config'] else result['device_name']}` |",
        f"| Precision | `{result['precision']}` |",
        f"| Mean ms | {latency['mean']} |",
        f"| P95 ms | {latency['p95']} |",
        f"| Generated tokens/s | {result['comparison']['ratios']['generated_tokens_per_second']} |",
        "",
        "## Text Generation",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Prompt token count | {text_generation['prompt_token_count']} |",
        f"| Generated token count | {text_generation['generated_token_count']} |",
        f"| Max new tokens | {text_generation['max_new_tokens']} |",
        f"| Download allowed | {text_generation['download_allowed']} |",
        "",
        "Prompt:",
        "",
        "```text",
        text_generation["prompt"],
        "```",
        "",
        "Generated text preview:",
        "",
        "```text",
        text_generation["generated_text"],
        "```",
        "",
        "## Notes",
        "",
        "- This is tiny text-generation path evidence, not a text quality benchmark.",
        "- `compare_ready` means the handoff envelope is complete; it does not imply a deployment approval.",
        "- The stable `yolo_env` remains separate from the isolated `llm_env` used for this smoke.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export LLM text-generation smoke as InferEdge-compatible metadata.json/result.json.")
    parser.add_argument("--llm-smoke", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    llm_smoke = args.llm_smoke or latest_llm_smoke()
    metadata, result = build_inferedge_llm_export(llm_smoke, args.output_dir, Path.cwd())
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
