#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    repo = Path(__file__).resolve().parents[1]
    path = repo / "benchmarks" / "tensorrt" / "resnet18_trtexec_smoke.py"
    spec = importlib.util.spec_from_file_location("resnet18_trtexec_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    text = """
    Throughput: 321.45 qps
    Latency: min = 2.90 ms, max = 4.56 ms, mean = 3.12 ms, median = 3.01 ms, percentile(90%) = 3.80 ms, percentile(95%) = 4.10 ms, percentile(99%) = 4.44 ms
    Enqueue Time: min = 0.39 ms, max = 0.50 ms, mean = 0.42 ms, median = 0.41 ms, percentile(90%) = 0.45 ms, percentile(95%) = 0.47 ms, percentile(99%) = 0.49 ms
    H2D Latency: min = 0.09 ms, max = 0.12 ms, mean = 0.10 ms, median = 0.10 ms, percentile(90%) = 0.11 ms, percentile(95%) = 0.11 ms, percentile(99%) = 0.12 ms
    GPU Compute Time: min = 2.70 ms, max = 4.00 ms, mean = 2.88 ms, median = 2.80 ms, percentile(90%) = 3.20 ms, percentile(95%) = 3.50 ms, percentile(99%) = 3.90 ms
    D2H Latency: min = 0.04 ms, max = 0.06 ms, mean = 0.05 ms, median = 0.05 ms, percentile(90%) = 0.05 ms, percentile(95%) = 0.06 ms, percentile(99%) = 0.06 ms
    """
    metrics = module.parse_trtexec_metrics(text)
    assert metrics["throughput_qps"] == 321.45
    assert metrics["latency_ms"]["mean"] == 3.12
    assert metrics["latency_ms"]["p95"] == 4.10
    assert metrics["gpu_compute_time_ms"]["median"] == 2.80
    assert metrics["gpu_compute_time_ms"]["p99"] == 3.90
    assert metrics["enqueue_time_ms"]["max"] == 0.50
    assert metrics["h2d_latency_ms"]["min"] == 0.09
    assert metrics["d2h_latency_ms"]["mean"] == 0.05
    assert metrics["percentile_99_ms"] == 4.44
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
