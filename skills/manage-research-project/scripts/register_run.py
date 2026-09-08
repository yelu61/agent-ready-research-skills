#!/usr/bin/env python3
"""Register mapped native-run metadata without conferring scientific readiness."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import os
from pathlib import Path

from project_contracts import (
    ContractError, load_json_object, resolve_project_relative,
    sha256_regular_file, utc_now,
)


TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "templates" / "provenance"


def append_runtime():
    """Check write requirements before creating directories or registry rows."""
    if any(not hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY")):
        raise ContractError("Registry writes require POSIX O_NOFOLLOW/O_DIRECTORY; use Linux, macOS or WSL. Dry run remains available.")
    try:
        return importlib.import_module("fcntl")
    except ImportError as exc:
        raise ContractError("Registry writes require fcntl locking; use Linux, macOS or WSL. Dry run remains available.") from exc


def artifact_id(analysis_id: str, path: str, digest: str) -> str:
    identity = json.dumps([analysis_id, path, digest], separators=(",", ":"))
    return "ART-" + hashlib.sha256(identity.encode()).hexdigest()[:20].upper()


def string_row(raw: dict, fields: list[str]) -> dict[str, str]:
    if not isinstance(raw, dict) or set(raw) - set(fields):
        raise ContractError("Record contains unknown registry fields")
    return {key: str(raw.get(key, "")) for key in fields}


def read_registry(root: Path, name: str) -> tuple[list[str], list[dict]]:
    template = TEMPLATES / name
    fields = template.read_text(encoding="utf-8").splitlines()[0].split("\t")
    path = resolve_project_relative(root, "provenance/" + name)
    if not path.exists():
        return fields, []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != fields:
            raise ContractError(f"{name}: registry header differs from the supported contract")
        return fields, list(reader)


def plan_registration(root: Path, document: dict) -> dict:
    run_fields, previous_runs = read_registry(root, "RUNS.tsv")
    artifact_fields, previous_artifacts = read_registry(root, "ARTIFACTS.tsv")
    run = string_row(document.get("run", {}), run_fields)
    if not run["run_id"] or not run["analysis_id"]:
        raise ContractError("run_id and analysis_id are required")
    raw_artifacts = document.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ContractError("artifacts must be a non-empty list")
    rows, directions, parents, identities = [], {}, {}, set()
    for raw in raw_artifacts:
        if not isinstance(raw, dict):
            raise ContractError("Each artifact must be an object")
        raw = dict(raw)
        direction = raw.pop("direction", "output")
        parent_paths = raw.pop("parent_paths", [])
        if direction not in {"input", "output", "delivery", "reference"} or not isinstance(parent_paths, list):
            raise ContractError("Invalid direction or parent_paths")
        row = string_row(raw, artifact_fields)
        path = resolve_project_relative(root, row["path"], must_exist=True)
        row["path"] = path.relative_to(root).as_posix()
        digest, size = sha256_regular_file(path)
        if row["sha256"] and row["sha256"] != digest:
            raise ContractError("Artifact checksum mismatch: " + row["path"])
        if row["size_bytes"] and row["size_bytes"] != str(size):
            raise ContractError("Artifact size mismatch: " + row["path"])
        if direction in {"reference", "input"}:
            existing = [item for item in previous_artifacts
                        if item["path"] == row["path"] and item["sha256"] == digest
                        and (direction == "reference" or item["analysis_id"] == run["analysis_id"])
                        and (not row["artifact_id"] or item["artifact_id"] == row["artifact_id"])]
            if len(existing) > 1 or (direction == "reference" and not existing):
                raise ContractError("Register the parent run first; reference must resolve uniquely: " + row["path"])
            if existing:
                row = dict(existing[0])
                if row["path"] in directions or row["artifact_id"] in identities:
                    raise ContractError("Duplicate reference: " + row["path"])
                directions[row["path"]] = direction
                identities.add(row["artifact_id"])
                parents[row["path"]] = []
                rows.append(row)
                continue
        row["analysis_id"] = row["analysis_id"] or run["analysis_id"]
        if row["analysis_id"] != run["analysis_id"]:
            raise ContractError("Artifact analysis_id differs from run")
        row["artifact_id"] = row["artifact_id"] or artifact_id(run["analysis_id"], row["path"], digest)
        if row["artifact_id"] in identities:
            raise ContractError("Duplicate artifact_id: " + row["artifact_id"])
        identities.add(row["artifact_id"])
        row["sha256"], row["size_bytes"] = digest, str(size)
        row["role"] = row["role"] or direction
        row["artifact_kind"] = row["artifact_kind"] or "other"
        row["evidence_purposes"] = row["evidence_purposes"] or "not_applicable"
        row["source_provenance_status"] = row["source_provenance_status"] or "unverified"
        row["access_class"] = row["access_class"] or "unknown"
        row["lifecycle_status"] = row["lifecycle_status"] or "current"
        if direction != "input":
            if row["run_id"] and row["run_id"] != run["run_id"]:
                raise ContractError("Output run_id differs from run")
            row["run_id"] = run["run_id"]
        existing = [item for item in previous_artifacts if item["artifact_id"] == row["artifact_id"]]
        row["recorded_at"] = row["recorded_at"] or (
            existing[0]["recorded_at"] if existing else utc_now()
        )
        if row["path"] in directions:
            raise ContractError("Duplicate artifact path: " + row["path"])
        directions[row["path"]] = direction
        parents[row["path"]] = parent_paths
        rows.append(row)
    path_ids = {row["path"]: row["artifact_id"] for row in rows}
    inputs = [row["artifact_id"] for row in rows if directions[row["path"]] == "input"]
    outputs = [row["artifact_id"] for row in rows if directions[row["path"]] == "output"]
    for row in rows:
        parent_paths = parents[row["path"]]
        if parent_paths:
            if any(path not in path_ids for path in parent_paths):
                raise ContractError("parent_paths must resolve to this registration's artifacts")
            row["parent_artifact_ids"] = ";".join(path_ids[path] for path in parent_paths)
        elif directions[row["path"]] == "output" and not row["parent_artifact_ids"]:
            row["parent_artifact_ids"] = ";".join(inputs)
    for key, ids in (("input_artifact_ids", inputs), ("output_artifact_ids", outputs)):
        if run[key] and set(run[key].split(";")) != set(ids):
            raise ContractError(key + " differs from registered directions")
        run[key] = ";".join(ids)
    for field in ("config_path", "invocation_path", "analysis_spec_path", "readiness_report_path", "log_path"):
        if run[field] and run[field] != "not_applicable":
            path = resolve_project_relative(root, run[field], must_exist=True)
            digest, _ = sha256_regular_file(path)
            hash_field = field.removesuffix("_path") + "_sha256"
            if hash_field in run:
                if run[hash_field] and run[hash_field] != digest:
                    raise ContractError("Run checksum mismatch: " + field)
                run[hash_field] = digest
    run["technical_validation_status"] = run["technical_validation_status"] or "not_assessed"

    def additions(proposed: list[dict], previous: list[dict], key: str) -> list[dict]:
        added = []
        for row in proposed:
            matching = [item for item in previous if item[key] == row[key]]
            if matching and (len(matching) != 1 or matching[0] != row):
                raise ContractError(f"Refusing to rebind existing {key}: {row[key]}")
            if not matching:
                added.append(row)
        return added

    return {
        "RUNS.tsv": (run_fields, additions([run], previous_runs, "run_id")),
        "ARTIFACTS.tsv": (artifact_fields, additions(rows, previous_artifacts, "artifact_id")),
    }


def append_registry(root: Path, name: str, fields: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    path = resolve_project_relative(root, "provenance/" + name)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t", lineterminator="\n")
    if not path.exists() or path.stat().st_size == 0:
        writer.writeheader()
    else:
        with path.open("rb") as existing:
            existing.seek(-1, os.SEEK_END)
            if existing.read(1) not in {b"\n", b"\r"}:
                buffer.write("\n")
    writer.writerows(rows)
    # Parent safety is checked by resolve_project_relative; O_NOFOLLOW also
    # prevents replacing the registry itself with a symlink before opening.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8", newline="") as handle:
        handle.write(buffer.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--metadata", required=True, help="Project-relative mapped JSON")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.project.is_symlink():
            raise ContractError("Project root must not be a symlink")
        root = args.project.resolve(strict=True)
        metadata = resolve_project_relative(root, args.metadata, must_exist=True)
        document = load_json_object(metadata)
        plan = plan_registration(root, document)
        if args.apply:
            fcntl = append_runtime()
            provenance = resolve_project_relative(root, "provenance")
            provenance.mkdir(exist_ok=True)
            # Serialize all importers on the provenance directory, without
            # leaving a new project-level lock or parallel registry file.
            fd = os.open(provenance, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                plan = plan_registration(root, document)
                for name, (fields, rows) in plan.items():
                    append_registry(root, name, fields, rows)
            finally:
                os.close(fd)
        print(json.dumps({"apply": args.apply, "added": {name: len(rows) for name, (_, rows) in plan.items()},
                          "scientific_readiness": "not_assessed"}))
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
