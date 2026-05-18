# V1 Completion Checklist

> v0.5 is a public runtime interaction milestone. V1 is complete only when this repo can act as a sustained Edge Runtime Evidence Lab for InferEdge reliability workflows, not just a collection of individual smoke tests.

## Current Baseline

| Area | v0.5 Status | Evidence |
|---|---|---|
| Environment and system baseline | Closed | [Day 1 environment check](day1_environment_check.md), [System baseline](system_baseline.md), [Resource map](../system/jetson_resource_map.md) |
| Runtime/provider comparison | Closed as bounded runtime comparison | [ResNet18 runtime matrix summary](resnet18_runtime_matrix_summary.md), [Runtime comparison](runtime_comparison.md) |
| Lightweight workloads | Closed as individual path evidence | [YOLO detection smoke](yolo_detection_smoke.md), [Whisper speech smoke](whisper_speech_transcription_smoke.md), [LLM text generation smoke](llm_text_generation_smoke.md) |
| Serving layer | Closed as localhost serving evidence | [FastAPI API usage](fastapi_api_usage.md), [FastAPI soak/burst](fastapi_soak_burst.md), [Serving boundary notes](serving_boundary_notes.md) |
| Multi-workload interaction | Closed as 30-second probe, 10-minute sustained run, 30-minute V1 gap run, compact runtime timeline export, p99/burst-window report, bounded degradation signal, and queue/serving observability | [Multi-workload sustained runtime](multi_workload_sustained_runtime.md), [Multi-workload runtime timeline](multi_workload_runtime_timeline.md), [Multi-workload burst window report](multi_workload_burst_window_report.md), [Multi-workload degradation signal](multi_workload_degradation_signal.md), [Multi-workload serving observability](multi_workload_serving_observability.md), [Multi-workload InferEdge export](multi_workload_sustained_inferedge_export.md) |
| InferEdge handoff | Closed for current evidence roles | [InferEdge schema validation](inferedge_schema_validation.md), [Portfolio evidence index](portfolio_evidence_index.md) |

## V1 Definition

Jetson Internal Lab reaches V1 when it can repeatedly run YOLO, Whisper, LLM, FastAPI serving, and telemetry workloads as a sustained internal edge runtime scenario, then export the resulting behavior as structured evidence that InferEdge Runtime, Orchestrator, AIGuard, or Lab can consume.

V1 does not mean production serving, robotics readiness, high accuracy, high availability, or a capacity plan. It means reproducible runtime reliability evidence under constrained Jetson conditions.

## Gap Checklist

| Priority | Gap | V1 Completion Condition | Current State | Next Action |
|---:|---|---|---|---|
| 1 | Longer sustained runtime | One 30-minute multi-workload run with YOLO loop, FastAPI ResNet18 concurrency, FastAPI Whisper burst, and `tegrastats` telemetry. | Closed by `multi_workload_sustained_20260518_002910`: 1800.0892s, 0 errors, raw logs, JSON result, Markdown report, and InferEdge export preserved. | Proceed to runtime timeline export. |
| 2 | Runtime timeline export | A compact timeline file that aligns workload events, latency windows, and `tegrastats` samples by timestamp. | Closed by `multi_workload_timeline_20260518_002910`: 181 buckets, 35,935 workload events, 1,799 `tegrastats` samples. | Proceed to p99 and burst-window reporting. |
| 3 | Latency distribution detail | Per-workload p50/p95/p99/max and before/during/after burst windows are reported in a way that can be compared across runs. | Closed by `multi_workload_burst_windows_20260518_002910`: 5 Whisper bursts, event-level p50/p95/p99/max, and telemetry deltas across before/during/after windows. | Proceed to bounded runtime degradation signal. |
| 4 | Runtime degradation signal | At least one bounded overload or contention scenario records latency spike, resource pressure, queue buildup, dropped request, or fallback behavior. | Closed by opt-in concurrency 8 runs; latest `multi_workload_degradation_signal_20260518_023351` records FastAPI p99 delta +580.2891ms, RAM avg delta +168.371MB, and no request errors. | Proceed to queue/serving observability. |
| 5 | Queue/serving observability | Serving evidence includes request counts, error counts, queue/backlog proxy, and dropped/failed request count. | Closed by `multi_workload_serving_observability_20260518_023351`: client max outstanding 8, server max in-flight 9, 6,060 client-completed requests, 0 failed/dropped proxy, and `/metrics` in-process counters preserved. | Proceed to InferEdge consumer handoff mapping. |
| 6 | InferEdge consumer handoff | Multi-workload artifacts have a documented handoff path for InferEdge Runtime/Orchestrator/AIGuard/Lab. | Closed by [InferEdge consumer handoff mapping](inferedge_consumer_handoff_mapping.md): Runtime, Orchestrator, AIGuard, and Lab field consumption is mapped with non-goal boundaries. | Proceed to schema drift protection. |
| 7 | Schema drift protection | CI validates every committed `metadata.json` / `result.json`, including multi-workload fields and artifact hashes. | Closed by [Schema drift protection review](schema_drift_protection_review.md): 11 handoff pairs pass strict artifact hash validation, and validation boundaries are documented. | Proceed to V1 public narrative and release notes. |
| 8 | V1 public narrative | README and release notes explain runtime reliability evidence, boundaries, and non-goals in one pass. | README and v0.5 release are aligned. | After gaps 1-7, publish `v1.0-runtime-evidence-lab` release notes. |

## Execution Order

1. Done: produce a 30-minute sustained multi-workload run.
2. Done: add timeline export for that run.
3. Done: add p99/burst-window reporting.
4. Done: add one opt-in overload/degradation scenario.
5. Done: add queue/serving observability with client outstanding and server in-flight proxies.
6. Done: document InferEdge ecosystem consumer mapping.
7. Done: document schema drift protection and keep validation green for all 11 handoff pairs.
8. Next: refresh public safety and prepare V1 release notes.

## Guardrails

- Do not add new models just to make the repo look larger.
- Do not claim production readiness, real-time behavior, or broad model accuracy.
- Do not compare different backend, precision, provider, or power-mode conditions as direct regressions.
- Do not break `metadata.json`, `result.json`, compare output, or existing schema validation.
- Keep `AGENTS.md` local-only and out of GitHub.

## V1 Exit Criteria

V1 is ready when the repo contains a reproducible 30-minute multi-workload runtime scenario, timeline-aware telemetry evidence, at least one bounded degradation signal, queue/serving observability evidence, InferEdge-compatible handoff artifacts, schema validation, public-safety review, and a release narrative that clearly states what the evidence proves and does not prove.
