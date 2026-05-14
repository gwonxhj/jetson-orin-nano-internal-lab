#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.inferedge_schema import (  # noqa: E402
    EXPORT_SCHEMA_VERSION,
    read_json,
    sha256_file,
    validate_inferedge_metadata,
    validate_inferedge_result,
)


class ValidationError(Exception):
    pass


def _path_from_repo(path_text: str, repo_root: Path) -> Path:
    if path_text.startswith("[home]/"):
        return Path.home() / path_text[len("[home]/"):]
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root / path


def _find_handoff_dirs(repo_root: Path) -> list[Path]:
    inferedge_root = repo_root / "results" / "inferedge"
    if not inferedge_root.exists():
        raise ValidationError("results/inferedge does not exist")
    return sorted(path for path in inferedge_root.iterdir() if path.is_dir())


def _validate_artifacts(metadata: dict[str, Any], result_path: Path, repo_root: Path, strict_files: bool) -> list[str]:
    artifacts = metadata.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        raise ValidationError("metadata.artifacts must be a non-empty list")

    runtime_artifacts = [artifact for artifact in artifacts if artifact.get("role") == "runtime_result"]
    if len(runtime_artifacts) != 1:
        raise ValidationError("metadata.artifacts must contain exactly one runtime_result artifact")

    checked_roles: list[str] = []
    for artifact in artifacts:
        role = artifact.get("role", "")
        path_text = artifact.get("path", "")
        digest = artifact.get("sha256", "")
        if not role:
            raise ValidationError("artifact role is empty")
        if not path_text:
            raise ValidationError(f"artifact {role} path is empty")
        if digest == "__FILLED_AFTER_WRITE__":
            raise ValidationError(f"artifact {role} still has placeholder sha256")
        if not digest:
            raise ValidationError(f"artifact {role} sha256 is empty")

        artifact_path = _path_from_repo(path_text, repo_root)
        if role == "runtime_result" and artifact_path.resolve() != result_path.resolve():
            raise ValidationError(f"runtime_result path does not point to result.json: {path_text}")
        if strict_files:
            if not artifact_path.exists() or not artifact_path.is_file():
                raise ValidationError(f"artifact {role} file is missing: {path_text}")
            actual = sha256_file(artifact_path)
            if actual != digest:
                raise ValidationError(f"artifact {role} sha256 mismatch: {path_text}")
        checked_roles.append(role)
    return checked_roles


def validate_handoff_dir(handoff_dir: Path, repo_root: Path, strict_files: bool = True) -> dict[str, Any]:
    metadata_path = handoff_dir / "metadata.json"
    result_path = handoff_dir / "result.json"
    if not metadata_path.exists():
        raise ValidationError(f"missing metadata.json in {handoff_dir}")
    if not result_path.exists():
        raise ValidationError(f"missing result.json in {handoff_dir}")

    metadata = read_json(metadata_path)
    result = read_json(result_path)
    validate_inferedge_metadata(metadata)
    validate_inferedge_result(result)

    if result.get("extra", {}).get("export_schema_version") != EXPORT_SCHEMA_VERSION:
        raise ValidationError("result extra.export_schema_version mismatch")
    if metadata.get("handoff", {}).get("consumer") != "InferEdgeLab":
        raise ValidationError("metadata handoff.consumer must be InferEdgeLab")
    if metadata.get("lab_compat", {}).get("runtime", {}).get("result_json_path") != str(result_path.relative_to(repo_root)):
        raise ValidationError("metadata lab_compat.runtime.result_json_path does not match handoff result.json")

    artifact_roles = _validate_artifacts(metadata, result_path, repo_root, strict_files)
    return {
        "handoff_dir": str(handoff_dir.relative_to(repo_root)),
        "runtime_role": result["runtime_role"],
        "compare_key": result["compare_key"],
        "backend_key": result["backend_key"],
        "verdict": result["comparison"]["verdict"],
        "artifact_roles": artifact_roles,
    }


def validate_all(repo_root: Path, strict_files: bool = True) -> dict[str, Any]:
    handoff_dirs = _find_handoff_dirs(repo_root)
    if not handoff_dirs:
        raise ValidationError("no InferEdge handoff directories found")

    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for handoff_dir in handoff_dirs:
        try:
            entries.append(validate_handoff_dir(handoff_dir, repo_root, strict_files=strict_files))
        except Exception as exc:
            errors.append({"handoff_dir": str(handoff_dir.relative_to(repo_root)), "error": str(exc)})

    return {
        "success": not errors,
        "validated_count": len(entries),
        "error_count": len(errors),
        "entries": entries,
        "errors": errors,
        "strict_files": strict_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate all results/inferedge metadata.json/result.json handoff pairs.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root. Defaults to this script's repository.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    parser.add_argument("--skip-artifact-files", action="store_true", help="Validate schema only; do not require artifact file existence or sha256 matches.")
    args = parser.parse_args()

    repo_root = args.root.resolve()
    summary = validate_all(repo_root, strict_files=not args.skip_artifact_files)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        status = "ok" if summary["success"] else "failed"
        print(f"inferedge validation {status}: {summary['validated_count']} valid, {summary['error_count']} errors")
        for entry in summary["entries"]:
            print(f"ok {entry['handoff_dir']} role={entry['runtime_role']} verdict={entry['verdict']}")
        for error in summary["errors"]:
            print(f"error {error['handoff_dir']}: {error['error']}")
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
