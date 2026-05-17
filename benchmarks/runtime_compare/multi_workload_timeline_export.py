#!/usr/bin/env python3
"""Export a compact runtime timeline from multi-workload sustained evidence.

The source multi-workload JSON keeps every workload event. This exporter aligns
those events with tegrastats side telemetry into fixed-width buckets so runtime
interaction can be inspected without re-reading the full raw event list.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "multi-workload-runtime-timeline-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}
    except Exception as exc:
        return {"command": command, "error": repr(exc)}


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def summarize_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "min": None, "p50": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return ordered[int(rank)]
        return ordered[low] * (high - rank) + ordered[high] * (rank - low)

    return {
        "count": len(values),
        "mean": _round(statistics.fmean(values)),
        "min": _round(min(values)),
        "p50": _round(percentile(0.50)),
        "p95": _round(percentile(0.95)),
        "p99": _round(percentile(0.99)),
        "max": _round(max(values)),
    }


def parse_tegrastats(log_path: Path, run_start: datetime) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    samples: list[dict[str, Any]] = []
    tz = run_start.tzinfo
    for line_no, line in enumerate(log_path.read_text(errors="replace").splitlines(), start=1):
        if len(line) < 19:
            continue
        try:
            sample_time = datetime.strptime(line[:19], "%m-%d-%Y %H:%M:%S").replace(tzinfo=tz)
        except ValueError:
            continue
        ram_match = re.search(r"RAM\s+(\d+)/(\d+)MB", line)
        gr3d_match = re.search(r"GR3D_FREQ\s+(\d+)%", line)
        vdd_match = re.search(r"VDD_IN\s+(\d+)mW", line)
        cpu_values = [float(value) for value in re.findall(r"(\d+)%@", line)]
        temps = [(name, float(value)) for name, value in re.findall(r"([A-Za-z0-9_]+)@([0-9.]+)C", line)]
        max_temp_name = ""
        max_temp_c: float | None = None
        if temps:
            max_temp_name, max_temp_c = max(temps, key=lambda item: item[1])
        gpu_temp = next((value for name, value in temps if name == "gpu"), None)
        samples.append({
            "line_no": line_no,
            "relative_s": round((sample_time - run_start).total_seconds(), 4),
            "wall_time": sample_time.isoformat(timespec="seconds"),
            "ram_used_mb": float(ram_match.group(1)) if ram_match else None,
            "ram_total_mb": float(ram_match.group(2)) if ram_match else None,
            "gr3d_freq_pct": float(gr3d_match.group(1)) if gr3d_match else None,
            "cpu_busy_pct_avg": round(statistics.fmean(cpu_values), 4) if cpu_values else None,
            "cpu_busy_pct_max": max(cpu_values) if cpu_values else None,
            "gpu_temp_c": gpu_temp,
            "max_temp_name": max_temp_name,
            "max_temp_c": max_temp_c,
            "vdd_in_mw": float(vdd_match.group(1)) if vdd_match else None,
        })
    return samples


def _bucket_index(relative_s: float, bucket_sec: float, bucket_count: int) -> int | None:
    if relative_s < 0:
        return None
    index = int(relative_s // bucket_sec)
    if index >= bucket_count:
        return bucket_count - 1
    return index


def _numeric(items: list[dict[str, Any]], key: str) -> list[float]:
    return [float(item[key]) for item in items if item.get(key) is not None]


def summarize_telemetry(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"sample_count": 0, "status": "no_samples"}
    max_temp_sample = max((sample for sample in samples if sample.get("max_temp_c") is not None), key=lambda sample: sample["max_temp_c"], default={})
    ram_values = _numeric(samples, "ram_used_mb")
    gr3d_values = _numeric(samples, "gr3d_freq_pct")
    cpu_avg_values = _numeric(samples, "cpu_busy_pct_avg")
    cpu_max_values = _numeric(samples, "cpu_busy_pct_max")
    gpu_temp_values = _numeric(samples, "gpu_temp_c")
    vdd_values = _numeric(samples, "vdd_in_mw")
    return {
        "sample_count": len(samples),
        "status": "parsed",
        "ram_used_mb_avg": _round(statistics.fmean(ram_values), 3) if ram_values else None,
        "ram_used_mb_max": _round(max(ram_values), 3) if ram_values else None,
        "gr3d_freq_pct_avg": _round(statistics.fmean(gr3d_values), 3) if gr3d_values else None,
        "gr3d_freq_pct_max": _round(max(gr3d_values), 3) if gr3d_values else None,
        "cpu_busy_pct_avg": _round(statistics.fmean(cpu_avg_values), 3) if cpu_avg_values else None,
        "cpu_busy_pct_max": _round(max(cpu_max_values), 3) if cpu_max_values else None,
        "gpu_temp_c_max": _round(max(gpu_temp_values), 3) if gpu_temp_values else None,
        "max_temp_name": max_temp_sample.get("max_temp_name", ""),
        "max_temp_c": _round(max_temp_sample.get("max_temp_c"), 3),
        "vdd_in_mw_avg": _round(statistics.fmean(vdd_values), 3) if vdd_values else None,
        "vdd_in_mw_max": _round(max(vdd_values), 3) if vdd_values else None,
    }


def summarize_workload(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {"event_count": 0, "success_count": 0, "error_count": 0, "latency_ms": summarize_values([]), "operations": {}}
    operations: dict[str, int] = {}
    for event in events:
        operation = str(event.get("operation", "unknown"))
        operations[operation] = operations.get(operation, 0) + 1
    return {
        "event_count": len(events),
        "success_count": sum(1 for event in events if event.get("ok") is True),
        "error_count": sum(1 for event in events if event.get("ok") is not True),
        "latency_ms": summarize_values([float(event["duration_ms"]) for event in events if event.get("duration_ms") is not None]),
        "operations": dict(sorted(operations.items())),
    }


def build_timeline(source_path: Path, repo_root: Path, bucket_sec: float) -> dict[str, Any]:
    evidence = read_json(source_path)
    metadata = evidence["metadata"]
    result = evidence["result"]
    if result.get("success") is not True or result.get("status") != "succeeded":
        raise ValueError("timeline export requires a successful multi-workload run")
    duration_s = float(result["scenario"]["duration_s"])
    bucket_count = int(math.ceil(duration_s / bucket_sec))
    generated_at = datetime.fromisoformat(metadata["generated_at"])
    run_start = generated_at - timedelta(seconds=duration_s)
    source_rel = str(source_path.resolve().relative_to(repo_root.resolve())) if source_path.is_absolute() else str(source_path)
    tegrastats_rel = metadata.get("tegrastats_log", "")
    tegrastats_path = repo_root / tegrastats_rel if tegrastats_rel else Path()
    telemetry_samples = parse_tegrastats(tegrastats_path, run_start) if tegrastats_rel else []

    buckets: list[dict[str, Any]] = []
    for index in range(bucket_count):
        buckets.append({
            "index": index,
            "start_s": round(index * bucket_sec, 4),
            "end_s": round(min((index + 1) * bucket_sec, duration_s), 4),
            "workloads": {},
            "telemetry": {"sample_count": 0, "status": "no_samples"},
            "flags": {"whisper_active": False, "event_errors": 0, "telemetry_present": False},
        })

    events_by_bucket: list[dict[str, list[dict[str, Any]]]] = [{} for _ in range(bucket_count)]
    for event in result["timeline"]:
        index = _bucket_index(float(event.get("started_at_s", 0.0)), bucket_sec, bucket_count)
        if index is None:
            continue
        workload = str(event.get("workload", "unknown"))
        events_by_bucket[index].setdefault(workload, []).append(event)

    telemetry_by_bucket: list[list[dict[str, Any]]] = [[] for _ in range(bucket_count)]
    for sample in telemetry_samples:
        index = _bucket_index(float(sample["relative_s"]), bucket_sec, bucket_count)
        if index is not None:
            telemetry_by_bucket[index].append(sample)

    for index, bucket in enumerate(buckets):
        for workload, events in sorted(events_by_bucket[index].items()):
            bucket["workloads"][workload] = summarize_workload(events)
        bucket["telemetry"] = summarize_telemetry(telemetry_by_bucket[index])
        bucket["flags"]["telemetry_present"] = bool(telemetry_by_bucket[index])
        bucket["flags"]["event_errors"] = sum(item["error_count"] for item in bucket["workloads"].values())
        bucket["flags"]["whisper_active"] = bool(bucket["workloads"].get("fastapi_whisper", {}).get("event_count", 0))

    workload_totals = {name: summarize_workload([event for event in result["timeline"] if event.get("workload") == name]) for name in sorted(result["summary_by_workload"])}
    whisper_events = [event for event in result["timeline"] if event.get("workload") == "fastapi_whisper"]
    spike_candidates = []
    for bucket in buckets:
        for workload, summary in bucket["workloads"].items():
            max_ms = summary["latency_ms"].get("max")
            if max_ms is not None:
                spike_candidates.append((float(max_ms), workload, bucket["index"]))
    spike_candidates.sort(reverse=True)

    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_json": source_rel,
            "source_sha256": sha256_file(source_path),
            "source_git_commit": metadata.get("git_commit", {}),
            "export_workspace_commit": run_command(["git", "rev-parse", "--short", "HEAD"]),
            "hostname": metadata.get("hostname", ""),
            "power_mode": metadata.get("power_mode", {}),
            "server_log": metadata.get("server_log", ""),
            "tegrastats_log": tegrastats_rel,
            "bucket_sec": bucket_sec,
        },
        "result": {
            "status": "succeeded",
            "success": True,
            "task": "multi_workload_runtime_timeline_export",
            "duration_s": duration_s,
            "run_start_estimated_at": run_start.isoformat(timespec="seconds"),
            "run_finished_at": generated_at.isoformat(timespec="seconds"),
            "bucket_count": bucket_count,
            "source_event_count": len(result["timeline"]),
            "telemetry_sample_count": len(telemetry_samples),
            "workload_totals": workload_totals,
            "telemetry_summary": summarize_telemetry(telemetry_samples),
            "whisper_bursts": [{"burst_index": event.get("details", {}).get("burst_index"), "started_at_s": event.get("started_at_s"), "ended_at_s": event.get("ended_at_s"), "duration_ms": event.get("duration_ms"), "ok": event.get("ok")} for event in whisper_events],
            "top_latency_buckets": [{"workload": workload, "bucket_index": index, "max_ms": _round(max_ms)} for max_ms, workload, index in spike_candidates[:10]],
            "buckets": buckets,
            "interpretation": {
                "deployment_ready_claim": False,
                "production_stress_test_claim": False,
                "accuracy_claim": False,
                "notes": [
                    "Timeline buckets align workload events and tegrastats telemetry for runtime interaction analysis.",
                    "Bucket summaries are not a production capacity plan or direct regression comparison.",
                ],
            },
        },
    }


def write_report(timeline: dict[str, Any], report_path: Path) -> None:
    result = timeline["result"]
    meta = timeline["metadata"]
    telemetry = result["telemetry_summary"]
    lines = [
        "# Multi-Workload Runtime Timeline Export",
        "",
        "> multi-workload evidence를 workload event + `tegrastats` bucket timeline으로 정리한 보고서입니다.",
        "> 이 timeline은 runtime interaction 분석용 evidence이며 production capacity plan이 아닙니다.",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Source JSON | `{meta['source_json']}` |",
        f"| Bucket size | {meta['bucket_sec']} s |",
        f"| Duration | {result['duration_s']} s |",
        f"| Buckets | {result['bucket_count']} |",
        f"| Workload events | {result['source_event_count']} |",
        f"| Tegrastats samples | {result['telemetry_sample_count']} |",
        "",
        "## Workload Totals",
        "",
        "| Workload | Events | Success | Errors | Mean ms | P95 ms | P99 ms | Max ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for workload, summary in result["workload_totals"].items():
        latency = summary["latency_ms"]
        lines.append(f"| {workload} | {summary['event_count']} | {summary['success_count']} | {summary['error_count']} | {latency['mean']} | {latency['p95']} | {latency['p99']} | {latency['max']} |")
    lines.extend([
        "",
        "## Telemetry Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| RAM used avg MB | {telemetry.get('ram_used_mb_avg')} |",
        f"| RAM used max MB | {telemetry.get('ram_used_mb_max')} |",
        f"| GR3D avg % | {telemetry.get('gr3d_freq_pct_avg')} |",
        f"| GR3D max % | {telemetry.get('gr3d_freq_pct_max')} |",
        f"| CPU busy avg % | {telemetry.get('cpu_busy_pct_avg')} |",
        f"| CPU busy max % | {telemetry.get('cpu_busy_pct_max')} |",
        f"| GPU temp max C | {telemetry.get('gpu_temp_c_max')} |",
        f"| VDD_IN avg mW | {telemetry.get('vdd_in_mw_avg')} |",
        f"| VDD_IN max mW | {telemetry.get('vdd_in_mw_max')} |",
        "",
        "## Whisper Bursts",
        "",
        "| Burst | Start s | End s | Duration ms | OK |",
        "|---:|---:|---:|---:|---|",
    ])
    for burst in result["whisper_bursts"]:
        lines.append(f"| {burst['burst_index']} | {burst['started_at_s']} | {burst['ended_at_s']} | {burst['duration_ms']} | {burst['ok']} |")
    lines.extend(["", "## Top Latency Buckets", "", "| Rank | Workload | Bucket | Max ms |", "|---:|---|---:|---:|"])
    for rank, item in enumerate(result["top_latency_buckets"], start=1):
        lines.append(f"| {rank} | {item['workload']} | {item['bucket_index']} | {item['max_ms']} |")
    lines.extend([
        "",
        "## Boundary",
        "",
        "- This is compact runtime interaction evidence, not a production load test.",
        "- Buckets summarize workload and telemetry behavior; raw logs remain the source of truth.",
        "- Use this artifact for timeline alignment, p99/burst-window analysis, and future degradation signal review.",
        "",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export compact runtime timeline from multi-workload sustained JSON.")
    parser.add_argument("--multi-workload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--bucket-sec", type=float, default=10.0)
    args = parser.parse_args()
    if args.bucket_sec <= 0:
        raise SystemExit("--bucket-sec must be positive")
    timeline = build_timeline(args.multi_workload, Path.cwd(), args.bucket_sec)
    write_json(args.output, timeline)
    print(args.output)
    if args.report is not None:
        write_report(timeline, args.report)
        print(args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
