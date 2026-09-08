#!/usr/bin/env python3
"""Validate the small 0.2-draft handoff structure and identifiers, not scientific truth."""
import argparse
import json
from pathlib import Path
import sys

VERSION = "0.2-draft"
STATUSES = {"BLOCKED", "REVIEW", "READY", "NOT_RUN"}
FEASIBILITY = {"feasible", "partial", "infeasible", "unknown"}


def validate(document, brief=None):
    errors = []
    if not isinstance(document, dict):
        return ["Document must be a JSON object."]

    def required_string(obj, key, label):
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            errors.append(f"{label}.{key} must be a nonempty string.")

    def record_list(key):
        value = document.get(key)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            errors.append(f"{key} must be a list of objects.")
            return []
        return value

    name = document.get("schema_name")
    if document.get("schema_version") != VERSION:
        errors.append(f"schema_version must be {VERSION}; migrate older drafts explicitly.")
    required_string(document, "question_id", "document")
    if name not in ("ReasoningBrief", "WorkflowReview", "RunEvidence"):
        return errors + ["Unknown schema_name."]
    boundary = document.get("claim_boundary")
    if name != "RunEvidence":
        if not isinstance(boundary, dict) or any(
            not isinstance(boundary.get(k), list) or any(not isinstance(v, str) for v in boundary[k])
            for k in ("supported", "exploratory", "unsupported")
        ):
            errors.append("claim_boundary requires supported/exploratory/unsupported lists of strings.")
    if name == "ReasoningBrief":
        required_string(document, "primary_question", "document")
        estimand = document.get("estimand")
        if not isinstance(estimand, dict) or "experimental_unit" not in estimand or (
            estimand["experimental_unit"] is not None and not isinstance(estimand["experimental_unit"], str)
        ):
            errors.append("estimand.experimental_unit must be a string or explicit null.")
        entries = record_list("required_evidence")
    elif name == "WorkflowReview":
        required_string(document, "review_id", "document")
        if document.get("overall_status") not in tuple(STATUSES):
            errors.append("Invalid overall_status.")
        for stage in record_list("stages"):
            required_string(stage, "stage", "stage")
            if stage.get("status") not in tuple(STATUSES):
                errors.append("Invalid stage status.")
        entries = record_list("evidence_coverage")
        for entry in entries:
            if entry.get("feasibility") not in tuple(FEASIBILITY):
                errors.append("Invalid evidence feasibility.")
    else:
        required_string(document, "run_id", "document")
        if document.get("execution_status") not in ("completed", "failed"):
            errors.append("RunEvidence requires executed status completed/failed, not a plan.")
        if document.get("quality_status") not in tuple(STATUSES - {"NOT_RUN"}):
            errors.append("Invalid RunEvidence quality_status.")
        for key, field in (("artifact", "path_or_key"), ("method", "name"), ("result", "summary")):
            obj = document.get(key)
            if not isinstance(obj, dict):
                errors.append(f"{key} must be an object.")
            else:
                required_string(obj, field, key)
        if not isinstance(document.get("method"), dict) or "version" not in document["method"]:
            errors.append("method.version must be recorded; use null plus a limitation if unknown.")
        elif document["method"]["version"] is not None and not isinstance(document["method"]["version"], str):
            errors.append("method.version must be a string or explicit null.")
        entries = [document]
    ids = []
    for entry in entries:
        required_string(entry, "evidence_id", "evidence")
        if isinstance(entry.get("evidence_id"), str):
            ids.append(entry["evidence_id"])
    if len(ids) != len(set(ids)):
        errors.append("Duplicate evidence_id.")
    if brief is not None:
        if not isinstance(brief, dict) or brief.get("schema_name") != "ReasoningBrief":
            errors.append("Upstream must be a ReasoningBrief.")
        else:
            errors.extend(f"Upstream: {error}" for error in validate(brief))
            if document.get("question_id") != brief.get("question_id"):
                errors.append("question_id differs from the upstream brief.")
            upstream_entries = brief.get("required_evidence")
            if not isinstance(upstream_entries, list):
                upstream_entries = []
            expected = {e["evidence_id"] for e in upstream_entries
                        if isinstance(e, dict) and isinstance(e.get("evidence_id"), str)}
            if name == "WorkflowReview" and set(ids) != expected:
                errors.append("WorkflowReview must cover each upstream evidence_id exactly once; update the brief before adding evidence.")
            elif name == "RunEvidence" and not set(ids).issubset(expected):
                errors.append("RunEvidence evidence_id is absent from the upstream brief.")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--brief", type=Path)
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        brief = json.loads(args.brief.read_text(encoding="utf-8")) if args.brief else None
        errors = validate(document, brief)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"valid_structure": not errors, "errors": errors,
                      "scope": "Structure/identifier checks only; not execution or scientific validation."}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
