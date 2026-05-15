#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    port = free_port()
    env = os.environ.copy()
    env["JETSON_LAB_SERVER_DEVICE"] = "cpu"
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.server.resnet18_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=repo,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fastapi_server_test.json"
            report = Path(tmp) / "fastapi_server_test.md"
            subprocess.run(
                [
                    sys.executable,
                    str(repo / "benchmarks" / "inference" / "fastapi_resnet18_client_smoke.py"),
                    "--base-url",
                    f"http://127.0.0.1:{port}",
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                    "--warmup",
                    "0",
                    "--repeat",
                    "1",
                    "--height",
                    "64",
                    "--width",
                    "64",
                ],
                cwd=repo,
                check=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            markdown = report.read_text(encoding="utf-8")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    assert payload["metadata"]["schema_version"] == "fastapi-server-smoke-v1"
    assert payload["result"]["task"] == "local_inference_api_smoke"
    assert payload["result"]["server"]["framework"] == "fastapi"
    assert payload["result"]["server"]["metrics_endpoint"] == "/metrics"
    metrics = payload["result"]["server"]["metrics"]["after"]
    assert metrics["schema_version"] == "fastapi-metrics-v1"
    assert metrics["status"] == "ok"
    assert metrics["runtime"]["device_default"] == "cpu"
    assert metrics["requests"]["by_path"]["/v1/infer/resnet18/synthetic"]["count"] >= 1
    assert payload["result"]["backend"] == "cpu"
    assert payload["result"]["input"]["shape"] == [1, 3, 64, 64]
    assert payload["result"]["latency"]["client_roundtrip_ms"]["count"] == 1
    assert payload["result"]["latency"]["server_inference_ms"]["count"] == 1
    assert "FastAPI ResNet18 Server Smoke Report" in markdown
    time.sleep(0.1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
