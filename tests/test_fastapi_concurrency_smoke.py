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
            output = Path(tmp) / "fastapi_concurrency_test.json"
            report = Path(tmp) / "fastapi_concurrency_test.md"
            subprocess.run(
                [
                    sys.executable,
                    str(repo / "benchmarks" / "inference" / "fastapi_concurrency_smoke.py"),
                    "--base-url",
                    f"http://127.0.0.1:{port}",
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                    "--levels",
                    "1,2",
                    "--requests-per-level",
                    "2",
                    "--warmup",
                    "0",
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

    assert payload["metadata"]["schema_version"] == "fastapi-concurrency-smoke-v1"
    assert payload["result"]["task"] == "local_inference_api_concurrency_smoke"
    assert payload["result"]["server"]["framework"] == "fastapi"
    assert payload["result"]["backend"] == "cpu"
    assert payload["result"]["input"]["shape"] == [1, 3, 64, 64]
    assert payload["result"]["runtime"]["concurrency_levels"] == [1, 2]
    assert len(payload["result"]["levels"]) == 2
    for level in payload["result"]["levels"]:
        assert level["success_count"] == level["requests"]
        assert level["error_count"] == 0
        assert level["client_roundtrip_ms"]["count"] == level["requests"]
        assert level["server_inference_ms"]["count"] == level["requests"]
    assert "FastAPI ResNet18 Concurrency Smoke Report" in markdown
    time.sleep(0.1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
