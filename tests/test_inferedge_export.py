#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import read_json, validate_inferedge_metadata, validate_inferedge_result


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inferedge"
        subprocess.run(
            [sys.executable, str(repo / "scripts" / "export_inferedge_evidence.py"), "--output-dir", str(out_dir)],
            cwd=repo,
            check=True,
        )
        metadata = read_json(out_dir / "metadata.json")
        result = read_json(out_dir / "result.json")

    validate_inferedge_metadata(metadata)
    validate_inferedge_result(result)
    assert result["schema_version"] == "inferedge-runtime-result-v1"
    assert result["extra"]["compare_ready"] is True
    assert result["comparison"]["comparability"]["same_model_hash"] is True
    assert result["comparison"]["comparability"]["same_input_shape"] is True
    assert result["comparison"]["comparability"]["same_precision"] is False
    assert result["comparison"]["ratios"]["mean_latency_pytorch_over_tensorrt"] > 1.0
    assert metadata["handoff"]["consumer"] == "InferEdgeLab"
    assert metadata["lab_compat"]["runtime"]["engine"] == "tensorrt"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
