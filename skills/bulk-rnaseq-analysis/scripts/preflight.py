#!/usr/bin/env python3
"""Preflight gate for bulk RNA-seq analyses.

Router picks a backend; preflight decides whether the *claim* a spec wants to
make is allowed by the backend's current capabilities, and stamps a readiness
record that is invalidated by any change to spec, inputs, or backend revision.

Commands:
  check   --spec S [--capabilities C] [--backend-revision R] [--readiness-out P]
  verify  --spec S --readiness R.json     # fail if any hash drifted

Exit codes: 0 ready, 3 blocked by a capability gate, 4 stale readiness,
2 invalid spec / usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CLAIM_ORDER = ["descriptive", "exploratory", "confirmatory", "predictive", "causal", "clinical"]

SPEC_ENUMS = {
    "claim_class": CLAIM_ORDER,
    "backend": ["rnaseq-templates", "tcga-toolkit"],
    "input_scale": ["raw-counts", "tpm", "log-tpm", "vst", "rlog", "normalized", "other"],
    "experimental_unit": ["sample", "patient", "cell"],
}
SPEC_REQUIRED = ["question", "claim_class", "backend", "task", "input_scale",
                 "experimental_unit", "design", "inputs"]

# Input scales a task family can never accept. Mirrors the router blocks so a
# spec that bypasses the router is still stopped here.
SCALE_BLOCKS = {
    "deg": {"tpm", "vst", "rlog", "normalized"},
    "limma-voom": {"vst", "rlog"},
    "tme": {"vst", "rlog"},
}


def fail_spec(errors: list[str]) -> int:
    for err in errors:
        print(f"spec error: {err}", file=sys.stderr)
    return 2


def validate_spec(spec: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    for field in SPEC_REQUIRED:
        if field not in spec:
            errors.append(f"missing required field: {field}")
    for field, allowed in SPEC_ENUMS.items():
        if field in spec and spec[field] not in allowed:
            errors.append(f"{field} must be one of {allowed}, got {spec[field]!r}")
    if "question" in spec and not str(spec["question"]).strip():
        errors.append("question must be non-empty")
    if "design" in spec and not isinstance(spec["design"], dict):
        errors.append("design must be an object")
    if "inputs" in spec and not isinstance(spec["inputs"], dict):
        errors.append("inputs must be an object mapping names to file paths")
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def get_path(spec: dict, dotted: str) -> object:
    node: object = spec
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def find_gate(capabilities: dict, backend: str, task: str) -> dict | None:
    for gate in capabilities.get("gates", []):
        if gate.get("backend") == backend and gate.get("task") == task:
            return gate
    return None


def evaluate(spec: dict, capabilities: dict) -> dict:
    """Return a verdict: ready/blocked + gate id + reasons + minimal fix."""
    backend, task = spec["backend"], spec["task"]
    claim = spec["claim_class"]

    blocked_scales = SCALE_BLOCKS.get(task, set())
    if spec["input_scale"] in blocked_scales:
        return {
            "verdict": "blocked",
            "gate_id": f"scale.{task}.{spec['input_scale']}",
            "reasons": [f"task '{task}' cannot accept {spec['input_scale']} input"],
            "min_fix": "Provide raw-counts input or choose a scale-compatible task.",
        }

    gate = find_gate(capabilities, backend, task)
    if gate is None:
        return {
            "verdict": "blocked",
            "gate_id": f"unknown.{backend}.{task}",
            "reasons": [f"no capability gate registered for {backend}/{task}"],
            "min_fix": "Register a gate in backend-capabilities.json after review.",
        }

    block_if = gate.get("block_if", {})
    if any(get_path(spec, path) == expected for path, expected in block_if.items()):
        return {
            "verdict": "blocked",
            "gate_id": gate["gate_id"],
            "reasons": [gate.get("block_reason", "blocked by capability gate")],
            "min_fix": gate.get("min_fix", ""),
        }

    max_claim = gate.get("max_claim_class", "exploratory")
    elevated = gate.get("elevated")
    if elevated and all(get_path(spec, path) is expected
                        for path, expected in elevated.get("requires", {}).items()):
        max_claim = elevated.get("max_claim_class", max_claim)

    if CLAIM_ORDER.index(claim) > CLAIM_ORDER.index(max_claim):
        return {
            "verdict": "blocked",
            "gate_id": gate["gate_id"],
            "reasons": [
                f"claim_class '{claim}' exceeds what {backend}/{task} supports "
                f"(max '{max_claim}'). Evidence: {gate.get('evidence', 'n/a')}"
            ],
            "min_fix": gate.get("min_fix", ""),
        }

    return {
        "verdict": "ready",
        "gate_id": gate["gate_id"],
        "max_claim_class": max_claim,
        "evidence": gate.get("evidence", ""),
        "reasons": [],
        "min_fix": "",
    }


def input_hashes(spec: dict, spec_dir: Path) -> tuple[dict, list[str]]:
    hashes: dict[str, str] = {}
    errors: list[str] = []
    for name, rel in spec.get("inputs", {}).items():
        path = Path(rel)
        if not path.is_absolute():
            path = spec_dir / path
        if not path.is_file():
            errors.append(f"input '{name}' not found: {path}")
            continue
        hashes[name] = sha256_file(path)
    return hashes, errors


def cmd_check(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    errors = validate_spec(spec)
    if errors:
        return fail_spec(errors)

    capabilities = json.loads(Path(args.capabilities).read_text(encoding="utf-8"))
    verdict = evaluate(spec, capabilities)

    in_hashes, hash_errors = input_hashes(spec, spec_path.parent)
    if hash_errors:
        return fail_spec(hash_errors)

    record = {
        "spec": str(spec_path),
        "spec_hash": canonical_hash(spec),
        "input_hashes": in_hashes,
        "backend_revision": args.backend_revision,
        "verdict": verdict,
    }
    out_path = Path(args.readiness_out or spec_path.with_suffix(".readiness.json"))
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(verdict, indent=2))
    print(f"readiness record: {out_path}")
    return 0 if verdict["verdict"] == "ready" else 3


def cmd_verify(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    record = json.loads(Path(args.readiness).read_text(encoding="utf-8"))

    problems: list[str] = []
    if canonical_hash(spec) != record.get("spec_hash"):
        problems.append("spec changed since readiness was issued")
    in_hashes, hash_errors = input_hashes(spec, spec_path.parent)
    if hash_errors:
        problems.extend(hash_errors)
    elif in_hashes != record.get("input_hashes"):
        changed = sorted(k for k in in_hashes if in_hashes[k] != record["input_hashes"].get(k))
        problems.append(f"inputs changed since readiness was issued: {', '.join(changed)}")
    if args.backend_revision and args.backend_revision != record.get("backend_revision"):
        problems.append(
            f"backend revision changed: {record.get('backend_revision')} -> {args.backend_revision}"
        )

    if problems:
        for problem in problems:
            print(f"STALE: {problem}", file=sys.stderr)
        return 4
    print("readiness is current")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    default_caps = Path(__file__).resolve().parent.parent / "assets" / "backend-capabilities.json"

    check = commands.add_parser("check", help="Evaluate a spec against capability gates")
    check.add_argument("--spec", required=True)
    check.add_argument("--capabilities", default=str(default_caps))
    check.add_argument("--backend-revision", default=None)
    check.add_argument("--readiness-out", default=None)

    verify = commands.add_parser("verify", help="Fail if spec/inputs/backend drifted")
    verify.add_argument("--spec", required=True)
    verify.add_argument("--readiness", required=True)
    verify.add_argument("--backend-revision", default=None)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "check":
        return cmd_check(args)
    return cmd_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
