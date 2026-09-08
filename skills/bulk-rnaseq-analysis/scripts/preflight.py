#!/usr/bin/env python3
"""Bulk RNA-seq capability audit and execution preflight.

check defaults to audit mode (no backend required, execution_ready=false).
execute mode requires a verified lock, checkout and reusable revision binding.
verify re-evaluates all bound evidence; freshness alone is never permission.
Exit codes: 0 compatible audit or execution-ready (inspect execution_ready),
3 blocked, 4 stale record, 2 invalid input/usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from analysis_contract import canonical_hash, read_json, scale_error, sha256_file, validate_json
from backend_lock import BackendLockError, read_lock, verify_checkout
from prediction_evidence import check_prediction_evidence

ASSETS = SCRIPT_DIR.parent / "assets"
SPEC_SCHEMA = ASSETS / "schemas" / "bulk-analysis-spec-v1.schema.json"
DEFAULT_CAPS = ASSETS / "backend-capabilities.json"
CLAIM_MODES = {"descriptive", "exploratory", "confirmatory", "predictive", "causal", "clinical"}


def validate_spec(spec: object) -> list[str]:
    errors = validate_json(spec, read_json(SPEC_SCHEMA))
    if not errors and spec["task"] in {"deg", "limma-voom", "time-course"}:
        if not spec["design"].get("formula", "").strip().startswith("~"):
            errors.append("design.formula must explicitly declare the model for this task")
    return errors


def validate_capabilities(caps: object) -> None:
    if not isinstance(caps, dict) or caps.get("version") != 2:
        raise ValueError("capability catalog v2 required; legacy total-order catalogs must be reviewed")
    if not isinstance(caps.get("gates"), list) or not isinstance(caps.get("bindings"), list):
        raise ValueError("capabilities require gates and bindings lists")
    pairs, ids = set(), set()
    for gate in caps["gates"]:
        if not isinstance(gate, dict):
            raise ValueError("invalid capability gate")
        pair = (gate.get("backend"), gate.get("task"))
        modes = gate.get("allowed_claim_modes")
        if (not all(isinstance(x, str) and x for x in pair)
                or not isinstance(gate.get("gate_id"), str) or not gate["gate_id"]
                or pair in pairs or gate["gate_id"] in ids
                or not isinstance(modes, list) or not modes
                or any(not isinstance(x, str) or x not in CLAIM_MODES for x in modes)
                or gate.get("status") not in {"available", "unavailable"}):
            raise ValueError("invalid/duplicate gate, status or explicit claim mode set")
        pairs.add(pair)
        ids.add(gate["gate_id"])


def find_gate(capabilities: dict, backend: str, task: str) -> dict | None:
    return next((g for g in capabilities["gates"]
                 if g["backend"] == backend and g["task"] == task), None)


def blocked(gate_id: str, reasons: list[str], fix: str) -> dict:
    return {"verdict": "blocked", "gate_id": gate_id, "reasons": reasons, "min_fix": fix}


def evaluate(spec: dict, capabilities: dict, spec_dir: Path | None = None) -> dict:
    """Gate compatibility only. A compatible result is not execution readiness."""
    validate_capabilities(capabilities)
    task, backend = spec["task"], spec["backend"]
    problem = scale_error(task, spec["input_scale"])
    if problem:
        return blocked(f"scale.{task}.{spec['input_scale']}", [problem],
                       "Provide a supported input scale (raw-counts for count engines) or select a reviewed compatible method.")
    gate = find_gate(capabilities, backend, task)
    if gate is None:
        return blocked(f"unknown.{backend}.{task}", ["no capability gate registered"],
                       "Plan/audit the request; register a scoped gate only after checking the backend implementation.")
    # R interactions include *, :, / nesting and ^ expansion. Quoted variable
    # names are excluded; arithmetic hidden in I() is conservative/needs review.
    formula = re.sub(r'\x60[^\x60]*\x60|"[^"]*"|\'[^\']*\'', "", spec["design"].get("formula", ""))
    if task == "time-course" and (spec["design"].get("interaction") is True
                                  or re.search(r"[:*/^]|%in%|\binteraction\s*\(", formula)):
        return blocked(gate["gate_id"], ["time-course only supports additive designs; formula contains an interaction/nesting/expansion or declares one"],
                       gate.get("min_fix", "Select a workflow supporting the scientific interaction question."))
    if gate["status"] != "available" or spec["claim_class"] not in gate["allowed_claim_modes"]:
        return blocked(gate["gate_id"],
                       [f"requested mode '{spec['claim_class']}' is not an available capability; declared modes: {gate['allowed_claim_modes']}"],
                       gate.get("min_fix", "Choose a supported question/mode; prediction is not causal evidence."))
    if task == "external-validation" and spec["claim_class"] == "predictive":
        problems = check_prediction_evidence(spec, spec_dir)
        if problems:
            return blocked(gate["gate_id"], problems, gate["min_fix"])
    return {"verdict": "compatible", "gate_id": gate["gate_id"],
            "allowed_claim_modes": gate["allowed_claim_modes"],
            "reasons": [], "min_fix": "", "evidence": gate.get("evidence", "")}


def input_hashes(spec: dict, spec_dir: Path) -> tuple[dict, list[str]]:
    hashes, errors = {}, []
    for name, rel in spec["inputs"].items():
        path = (spec_dir / rel).resolve()
        if not path.is_file():
            errors.append(f"input '{name}' not found: {path}")
        else:
            hashes[name] = sha256_file(path)
    return hashes, errors


def review_evidence(path: Path, lock: dict, capabilities: dict) -> tuple[list[str], dict]:
    """Check review identity, coverage, nonempty artifact bytes and drift.

    Artifact contents remain an assessor's scientific responsibility. This code
    validates a recorded review, not its scientific truth.
    """
    review = read_json(path)
    if not isinstance(review, dict) or review.get("schema_version") != "backend-capability-review/v1":
        raise ValueError("review must use backend-capability-review/v1")
    if any(review.get(k) != lock[k] for k in ("backend", "source_url", "revision")):
        raise ValueError("capability review does not match backend lock source/revision")
    expected_catalog = canonical_hash({k: v for k, v in capabilities.items() if k != "bindings"})
    if review.get("catalog_hash") != expected_catalog:
        raise ValueError("review must identify the exact capability catalog it assessed")
    for key in ("assessor", "reviewed_at", "scope"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError(f"review requires {key}")
    checks = review.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("review requires nonempty gate checks with evidence artifacts")
    available = {g["gate_id"] for g in capabilities["gates"] if g["backend"] == lock["backend"]}
    hashes, gates = {"review": sha256_file(path)}, []
    for check in checks:
        if not isinstance(check, dict) or check.get("gate_id") not in available:
            raise ValueError("review references an unknown backend gate")
        if check.get("result") != "pass" or check.get("kind") not in {"contract-test", "source-review"}:
            raise ValueError("only recorded passing contract-tests/source-reviews can bind capability")
        if not isinstance(check.get("artifact"), str) or not check["artifact"]:
            raise ValueError("review check requires an evidence artifact")
        artifact = (path.parent / check["artifact"]).resolve()
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError("review evidence artifact missing or empty")
        digest = sha256_file(artifact)
        if digest != check.get("sha256"):
            raise ValueError("review evidence artifact digest mismatch")
        gates.append(check["gate_id"])
        hashes[str(artifact)] = digest
    return sorted(set(gates)), hashes


def execution_binding(spec: dict, caps: dict, caps_path: Path,
                      lock_path: Path | None, root: Path | None) -> dict:
    if not lock_path or not root:
        raise ValueError("execution needs --backend-lock and --backend-root; use --mode audit while preparing them")
    lock = read_lock(lock_path)
    if lock["backend"] != spec["backend"]:
        raise ValueError("backend lock does not match spec backend")
    checkout = verify_checkout(lock, root)
    matches = [b for b in caps["bindings"] if isinstance(b, dict)
               and all(b.get(k) == lock[k] for k in ("backend", "source_url", "revision"))]
    if len(matches) != 1:
        raise ValueError("no unique capability binding for this source/revision; run bind-capabilities with existing revision-specific review evidence")
    binding = matches[0]
    evidence = binding.get("review_evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str):
        raise ValueError("binding requires review_evidence.path and sha256")
    path = (caps_path.parent / evidence["path"]).resolve()
    if not path.is_file() or sha256_file(path) != evidence.get("sha256"):
        raise ValueError("capability review evidence is missing or drifted")
    gates, hashes = review_evidence(path, lock, caps)
    gate = find_gate(caps, spec["backend"], spec["task"])
    if gate is None or gate["gate_id"] not in gates or gates != binding.get("gate_ids"):
        raise ValueError("review evidence does not cover this gate or binding coverage drifted")
    if binding.get("catalog_hash") != canonical_hash({k: v for k, v in caps.items() if k != "bindings"}):
        raise ValueError("capability declarations changed after review binding")
    return {"lock": lock, "lock_hash": sha256_file(lock_path), "checkout": checkout,
            "evidence_hashes": hashes}


def fingerprints(caps_path: Path) -> dict:
    paths = {"capabilities": caps_path, "spec_schema": SPEC_SCHEMA,
             "lock_schema": ASSETS / "schemas" / "backend-lock-v1.schema.json"}
    for name in ("preflight.py", "analysis_contract.py", "prediction_evidence.py", "backend_lock.py"):
        paths[f"evaluator:{name}"] = SCRIPT_DIR / name
    return {key: sha256_file(path) for key, path in paths.items()}


def make_record(spec_path: Path, caps_path: Path, mode: str,
                lock_path: Path | None, root: Path | None) -> dict:
    spec = read_json(spec_path)
    errors = validate_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    caps = read_json(caps_path)
    verdict = evaluate(spec, caps, spec_path.parent)
    hashes, errors = input_hashes(spec, spec_path.parent)
    if errors:
        raise ValueError("; ".join(errors))
    binding = None
    if mode == "execute":
        if not spec["inputs"]:
            verdict = blocked("inputs.missing", ["execution requires actual analysis input files"],
                              "Register the real input files in spec.inputs; an empty input set is planning-only.")
        try:
            binding = execution_binding(spec, caps, caps_path, lock_path, root)
        except (ValueError, OSError, BackendLockError) as exc:
            if verdict["verdict"] != "blocked":
                verdict = blocked("backend.binding", [], "")
            verdict["reasons"].append(str(exc))
            verdict["min_fix"] += " Obtain a clean locked checkout and reuse or create its revision-specific capability binding; planning/audit remain available."
    ready = mode == "execute" and binding is not None and verdict["verdict"] == "compatible"
    verdict["capability_verdict"] = verdict["verdict"]
    verdict["verdict"] = "ready" if ready else ("plan-only" if verdict["verdict"] == "compatible" else "blocked")
    verdict["execution_ready"] = ready
    verdict["scientific_certification"] = False
    return {"record_schema": "bulk-readiness/v2", "spec": str(spec_path.resolve()),
            "capabilities_path": str(caps_path.resolve()), "mode": mode,
            "backend_lock_path": str(lock_path.resolve()) if lock_path else None,
            "backend_root": str(root.resolve()) if root else None,
            "spec_hash": canonical_hash(spec), "input_hashes": hashes,
            "dependencies": fingerprints(caps_path), "backend_binding": binding,
            "verdict": verdict}


def cmd_check(args) -> int:
    record = make_record(args.spec.resolve(), args.capabilities.resolve(), args.mode,
                         args.backend_lock, args.backend_root)
    out = args.readiness_out or args.spec.with_suffix(".readiness.json")
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record["verdict"], indent=2))
    print(f"readiness record: {out}")
    return 3 if record["verdict"]["verdict"] == "blocked" else 0


def cmd_verify(args) -> int:
    record = read_json(args.readiness)
    if not isinstance(record, dict) or record.get("record_schema") != "bulk-readiness/v2":
        print("STALE: legacy/invalid readiness; run check again", file=sys.stderr)
        return 4
    try:
        current = make_record(args.spec.resolve(),
                              (args.capabilities or Path(record["capabilities_path"])).resolve(),
                              record["mode"],
                              args.backend_lock or (Path(record["backend_lock_path"]) if record["backend_lock_path"] else None),
                              args.backend_root or (Path(record["backend_root"]) if record["backend_root"] else None))
    except (ValueError, OSError, BackendLockError, KeyError, TypeError) as exc:
        print(f"STALE: {exc}", file=sys.stderr)
        return 4
    if current != record:
        print("STALE: spec, inputs, capability/schema/evaluator, lock, checkout or review evidence changed; rerun check", file=sys.stderr)
        return 4
    print(json.dumps({"freshness": "current", **current["verdict"]}, indent=2))
    return 3 if current["verdict"]["verdict"] == "blocked" else 0


def cmd_bind(args) -> int:
    caps = read_json(args.capabilities)
    validate_capabilities(caps)
    lock = read_lock(args.backend_lock)
    verify_checkout(lock, args.backend_root)
    gates, _ = review_evidence(args.review_evidence.resolve(), lock, caps)
    caps["bindings"] = [{**{k: lock[k] for k in ("backend", "source_url", "revision")},
                         "gate_ids": gates,
                         "catalog_hash": canonical_hash({k: v for k, v in caps.items() if k != "bindings"}),
                         "review_evidence": {"path": str(args.review_evidence.resolve()),
                                             "sha256": sha256_file(args.review_evidence)}}]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(caps, indent=2) + "\n")
    print(json.dumps({"status": "bound", "revision": lock["revision"],
                      "gate_ids": gates, "output": str(args.output)}, indent=2))
    return 0


def cmd_prepare_review(args) -> int:
    caps, lock = read_json(args.capabilities), read_lock(args.backend_lock)
    validate_capabilities(caps)
    available = {g["gate_id"] for g in caps["gates"] if g["backend"] == lock["backend"]}
    if not set(args.gate_id).issubset(available):
        raise ValueError("requested review gate does not belong to this backend")
    document = {"schema_version": "backend-capability-review/v1",
                **{k: lock[k] for k in ("backend", "source_url", "revision")},
                "catalog_hash": canonical_hash({k: v for k, v in caps.items() if k != "bindings"}),
                "assessor": "", "reviewed_at": date.today().isoformat(), "scope": "",
                "checks": [{"gate_id": g, "result": "not-assessed", "kind": "source-review",
                            "artifact": "", "sha256": ""} for g in sorted(set(args.gate_id))]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(document, indent=2) + "\n")
    print(f"Unassessed review template: {args.output}; attach actual evidence before binding.")
    return 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Audit a spec; explicitly request execute mode for readiness")
    check.add_argument("--spec", type=Path, required=True)
    check.add_argument("--mode", choices=("audit", "execute"), default="audit")
    check.add_argument("--capabilities", type=Path, default=DEFAULT_CAPS)
    check.add_argument("--backend-lock", type=Path)
    check.add_argument("--backend-root", type=Path)
    check.add_argument("--readiness-out", type=Path)
    verify = commands.add_parser("verify", help="Re-evaluate evidence and preserve blocked/plan-only state")
    verify.add_argument("--spec", type=Path, required=True)
    verify.add_argument("--readiness", type=Path, required=True)
    verify.add_argument("--capabilities", type=Path)
    verify.add_argument("--backend-lock", type=Path)
    verify.add_argument("--backend-root", type=Path)
    bind = commands.add_parser("bind-capabilities", help="Save a reusable binding to reviewed backend evidence")
    bind.add_argument("--capabilities", type=Path, default=DEFAULT_CAPS)
    bind.add_argument("--backend-lock", type=Path, required=True)
    bind.add_argument("--backend-root", type=Path, required=True)
    bind.add_argument("--review-evidence", type=Path, required=True)
    bind.add_argument("--output", type=Path, required=True)
    prepare = commands.add_parser("prepare-review", help="Create an unassessed exact-revision review template")
    prepare.add_argument("--capabilities", type=Path, default=DEFAULT_CAPS)
    prepare.add_argument("--backend-lock", type=Path, required=True)
    prepare.add_argument("--gate-id", action="append", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return {"check": cmd_check, "verify": cmd_verify, "bind-capabilities": cmd_bind,
                "prepare-review": cmd_prepare_review}[args.command](args)
    except (ValueError, OSError, BackendLockError, KeyError, TypeError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
