#!/usr/bin/env python3
"""Audit project structure, portability, document freshness and source integrity."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from project_contracts import (
    ContractError,
    load_json_object,
    resolve_project_relative,
    verify_source_manifest_document,
)
from scaffold_project import profile_spec


AUDIT_SCHEMA = "project-structure-audit/v2"
EXCLUDED_PARTS = {".git", ".archive", "data/raw", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".r", ".R", ".sh", ".yaml", ".yml", ".toml"}
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:/Users/|/home/|[A-Za-z]:[\\/]"
    r"|(?<!\\)\\\\(?:\?\\)?[^\\\s]+\\[^\\\s]+)"
)
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


def issue(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def safe_regular_project_file(
    root: Path, relative: str, findings: list[dict[str, str]]
) -> Path | None:
    """Return a local regular file without following any project symlink."""
    candidate = root / relative
    if candidate.is_symlink():
        findings.append(
            issue(
                "error",
                "path-symlink",
                relative,
                "Audit inputs must not be symlinks.",
            )
        )
        return None
    if not candidate.exists():
        return None
    try:
        resolved = resolve_project_relative(root, relative, must_exist=True)
    except ContractError as exc:
        findings.append(issue("error", "path-unsafe", relative, str(exc)))
        return None
    if not resolved.is_file():
        findings.append(
            issue("warning", "file-type", relative, "Expected a regular file.")
        )
        return None
    return resolved


def relative_parts(path: Path, root: Path) -> set[str]:
    parts = path.relative_to(root).parts
    cumulative = {parts[0]} if parts else set()
    if len(parts) >= 2:
        cumulative.add("/".join(parts[:2]))
    return cumulative | set(parts)


def scan_absolute_paths(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    candidates = [
        root / "docs",
        root / "scripts",
        root / "notebooks",
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / "README.md",
        root / "PIPELINE.md",
    ]
    files: list[Path] = []
    for candidate in candidates:
        candidate_relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            findings.append(
                issue(
                    "error",
                    "path-symlink",
                    candidate_relative,
                    "Audit inputs must not be symlinks.",
                )
            )
            continue
        if candidate.is_file():
            files.append(candidate)
        elif candidate.is_dir():
            try:
                for path in candidate.rglob("*"):
                    relative = path.relative_to(root).as_posix()
                    if path.is_symlink():
                        findings.append(
                            issue(
                                "error",
                                "path-symlink",
                                relative,
                                "Audit inputs must not contain symlinks.",
                            )
                        )
                        continue
                    try:
                        resolve_project_relative(root, relative)
                    except ContractError as exc:
                        findings.append(
                            issue("error", "path-unsafe", relative, str(exc))
                        )
                        continue
                    if path.is_file():
                        files.append(path)
            except OSError as exc:
                findings.append(
                    issue(
                        "warning",
                        "source-scan",
                        str(candidate.relative_to(root)),
                        str(exc),
                    )
                )
    for path in sorted(set(files)):
        if relative_parts(path, root) & EXCLUDED_PARTS:
            continue
        try:
            if path.suffix == ".ipynb":
                notebook = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(notebook, dict):
                    raise TypeError("Notebook root must be a JSON object")
                cells = notebook.get("cells", [])
                if not isinstance(cells, list):
                    raise TypeError("Notebook cells must be a list")
                text = "\n".join(
                    "".join(cell.get("source", []))
                    for cell in cells
                    if isinstance(cell, dict) and cell.get("cell_type") == "code"
                )
            elif path.suffix in TEXT_SUFFIXES or path.name in {
                "AGENTS.md",
                "CLAUDE.md",
            }:
                text = path.read_text(encoding="utf-8")
            else:
                continue
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
            findings.append(
                issue(
                    "warning",
                    "source-read",
                    str(path.relative_to(root)),
                    str(exc),
                )
            )
            continue
        if ABSOLUTE_PATH_RE.search(text):
            findings.append(
                issue(
                    "warning",
                    "absolute-path",
                    str(path.relative_to(root)),
                    "Active source contains a machine-specific absolute path.",
                )
            )
    return findings


def parse_last_updated(path: Path) -> date | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"Cannot read update date: {exc}") from exc
    match = re.search(
        r"(?:Last updated|Updated|更新日期)\s*:\s*(\d{4}-\d{2}-\d{2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise ContractError(f"Invalid update date: {match.group(1)}") from exc


def extract_next_task(path: Path) -> tuple[bool, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False, None
    match = re.search(
        r"^##\s+Next minimal executable task\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not match:
        return False, None
    lines = [
        re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line.strip())
        for line in match.group("body").splitlines()
        if line.strip() and not line.lstrip().startswith("<!--")
    ]
    value = " ".join(lines).strip()
    if not value or "TODO" in value.upper():
        return True, None
    return True, re.sub(r"\s+", " ", value).casefold()


def check_manifest_targets(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    try:
        manifests = sorted(root.rglob("*MANIFEST.tsv"))
    except OSError as exc:
        return [issue("error", "manifest-scan", ".", str(exc))]
    for path in manifests:
        try:
            relative_manifest = path.relative_to(root)
        except ValueError:
            continue
        if ".archive" in relative_manifest.parts:
            continue
        if path.is_symlink():
            findings.append(
                issue(
                    "error",
                    "path-symlink",
                    relative_manifest.as_posix(),
                    "Manifest inputs must not be symlinks.",
                )
            )
            continue
        try:
            resolve_project_relative(
                root, relative_manifest.as_posix(), must_exist=True
            )
        except ContractError as exc:
            findings.append(
                issue(
                    "error",
                    "manifest-target-unsafe",
                    relative_manifest.as_posix(),
                    str(exc),
                )
            )
            continue
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if reader.fieldnames is None:
                    raise ValueError("Manifest has no header")
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            findings.append(
                issue("error", "manifest-read", relative_manifest.as_posix(), str(exc))
            )
            continue
        for row_number, row in enumerate(rows, start=2):
            for key, value in row.items():
                if not isinstance(key, str) or "path" not in key.casefold():
                    continue
                if not isinstance(value, str) or not value.strip():
                    continue
                for raw in value.split(";"):
                    target = raw.strip().strip("`")
                    if not target or target.upper().startswith("TODO"):
                        continue
                    if target.casefold() in {"na", "n/a", "none", "not_applicable"}:
                        continue
                    if URI_SCHEME_RE.match(target):
                        try:
                            parsed = urlsplit(target)
                            allowed_external = (
                                parsed.scheme == "https"
                                and bool(parsed.hostname)
                                and parsed.username is None
                                and parsed.password is None
                            )
                        except ValueError:
                            allowed_external = False
                        if allowed_external:
                            continue
                        findings.append(
                            issue(
                                "error",
                                "manifest-target-unsafe",
                                relative_manifest.as_posix(),
                                f"Row {row_number}, {key}: only credential-free HTTPS external references are allowed.",
                            )
                        )
                        continue
                    if any(token in target for token in ("[", "*", "{{")):
                        continue
                    try:
                        destination = resolve_project_relative(root, target)
                    except ContractError as exc:
                        findings.append(
                            issue(
                                "error",
                                "manifest-target-unsafe",
                                relative_manifest.as_posix(),
                                f"Row {row_number}, {key}: {exc}",
                            )
                        )
                        continue
                    if not destination.exists():
                        findings.append(
                            issue(
                                "warning",
                                "manifest-target",
                                relative_manifest.as_posix(),
                                f"Row {row_number}, {key}: target not found: {target}",
                            )
                        )
    return findings


def structure_status(findings: list[dict[str, str]]) -> str:
    if any(item["level"] == "error" for item in findings):
        return "fail"
    if any(item["level"] == "warning" for item in findings):
        return "warn"
    return "pass"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit project structure and source integrity. This command does not "
            "assess scientific readiness."
        )
    )
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--profile",
        choices=["minimal", "research", "manuscript"],
        default="research",
    )
    parser.add_argument("--stale-days", type=int, default=30)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.stale_days < 0:
        parser.error("--stale-days must be non-negative")

    root = args.target.expanduser().resolve()
    structure_findings: list[dict[str, str]] = []
    source_findings: list[dict[str, str]] = []
    source_integrity = "not_assessed"
    source_manifest_contract = "not_assessed"
    if not root.is_dir():
        structure_findings.append(
            issue(
                "error",
                "missing-root",
                str(root),
                "Project directory does not exist.",
            )
        )
    else:
        _, required_files = profile_spec(args.profile)
        for relative in required_files:
            path = safe_regular_project_file(root, relative, structure_findings)
            if (
                path is None
                and not (root / relative).exists()
                and not (root / relative).is_symlink()
            ):
                structure_findings.append(
                    issue(
                        "warning",
                        "missing-file",
                        relative,
                        "Recommended project file is missing; document an accepted equivalent or scaffold it.",
                    )
                )

        agents = safe_regular_project_file(root, "AGENTS.md", structure_findings)
        if agents is not None:
            try:
                agents_text = agents.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                structure_findings.append(
                    issue("warning", "agents-read", "AGENTS.md", str(exc))
                )
            else:
                if "data/raw" not in agents_text:
                    structure_findings.append(
                        issue(
                            "warning",
                            "raw-protection",
                            "AGENTS.md",
                            "Raw-data protection is not explicit.",
                        )
                    )

        document_paths: dict[str, Path | None] = {}
        for relative in ("docs/PROJECT_STATUS.md", "docs/SESSION_HANDOFF.md"):
            path = safe_regular_project_file(root, relative, structure_findings)
            document_paths[relative] = path
            if path is None:
                continue
            try:
                updated = parse_last_updated(path)
            except ContractError as exc:
                structure_findings.append(
                    issue("warning", "invalid-date", relative, str(exc))
                )
                continue
            if updated is None:
                structure_findings.append(
                    issue(
                        "warning",
                        "missing-date",
                        relative,
                        "No parseable Last updated date.",
                    )
                )
            elif (date.today() - updated).days > args.stale_days:
                structure_findings.append(
                    issue(
                        "warning",
                        "stale-document",
                        relative,
                        f"Last updated {(date.today() - updated).days} days ago.",
                    )
                )

        status_path = document_paths["docs/PROJECT_STATUS.md"]
        handoff_path = document_paths["docs/SESSION_HANDOFF.md"]
        status_present, status_task = (
            extract_next_task(status_path) if status_path else (False, None)
        )
        handoff_present, handoff_task = (
            extract_next_task(handoff_path) if handoff_path else (False, None)
        )
        if status_path is not None and not status_present:
            structure_findings.append(
                issue(
                    "warning",
                    "next-task",
                    "docs/PROJECT_STATUS.md",
                    "No next minimal executable task section.",
                )
            )
        if handoff_path is not None and not handoff_present:
            structure_findings.append(
                issue(
                    "warning",
                    "next-task",
                    "docs/SESSION_HANDOFF.md",
                    "No next minimal executable task section.",
                )
            )
        if status_task and handoff_task and status_task != handoff_task:
            structure_findings.append(
                issue(
                    "warning",
                    "next-task-mismatch",
                    "docs/SESSION_HANDOFF.md",
                    "The handoff next task differs from PROJECT_STATUS.md.",
                )
            )
        elif (status_task is None) != (handoff_task is None):
            structure_findings.append(
                issue(
                    "warning",
                    "next-task-incomplete",
                    "docs/",
                    "Only one of PROJECT_STATUS.md and SESSION_HANDOFF.md has a concrete next task.",
                )
            )

        todo_count = 0
        docs = root / "docs"
        if docs.is_symlink():
            structure_findings.append(
                issue(
                    "error",
                    "path-symlink",
                    "docs",
                    "Audit inputs must not be symlinks.",
                )
            )
            document_candidates: list[Path] = []
        else:
            document_candidates = list(docs.glob("*.md")) if docs.is_dir() else []
        for candidate in document_candidates:
            relative = candidate.relative_to(root).as_posix()
            path = safe_regular_project_file(root, relative, structure_findings)
            if path is None:
                continue
            try:
                todo_count += len(
                    re.findall(r"\bTODO:", path.read_text(encoding="utf-8"))
                )
            except (OSError, UnicodeError) as exc:
                structure_findings.append(
                    issue(
                        "warning",
                        "document-read",
                        str(path.relative_to(root)),
                        str(exc),
                    )
                )
        if todo_count:
            structure_findings.append(
                issue(
                    "info",
                    "todo-count",
                    "docs/",
                    f"{todo_count} unresolved TODO placeholders; structure may pass while scientific readiness remains unassessed.",
                )
            )

        legacy_locations: list[str] = []
        for relative in ("docs/RESULTS_SUMMARY.md", "PIPELINE.md"):
            path = safe_regular_project_file(root, relative, structure_findings)
            if path is None:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if re.search(
                r"Evidence state|`confirmed`\s*,\s*`supported`|\|\s*confirmed\s*\|",
                text,
                re.IGNORECASE,
            ):
                legacy_locations.append(relative)
        if legacy_locations:
            structure_findings.append(
                issue(
                    "info",
                    "legacy-evidence-state",
                    ";".join(legacy_locations),
                    "Legacy single-axis evidence states require review; do not auto-upgrade confirmed/supported claims.",
                )
            )

        structure_findings.extend(scan_absolute_paths(root))
        structure_findings.extend(check_manifest_targets(root))

        source_manifest = safe_regular_project_file(
            root, "provenance/SOURCE_MANIFEST.json", structure_findings
        )
        if source_manifest is not None:
            try:
                source_report = verify_source_manifest_document(
                    root, load_json_object(source_manifest)
                )
            except ContractError as exc:
                source_manifest_contract = "invalid"
                source_findings.append(
                    issue(
                        "error",
                        "source-manifest-read",
                        "provenance/SOURCE_MANIFEST.json",
                        str(exc),
                    )
                )
            else:
                source_manifest_contract = source_report["manifest_contract_status"]
                source_integrity = source_report["source_integrity_status"]
                source_findings.extend(source_report["findings"])

    findings = structure_findings + source_findings
    counts = {
        level: sum(item["level"] == level for item in findings)
        for level in ("error", "warning", "info")
    }
    report = {
        "schema_version": AUDIT_SCHEMA,
        "audit_kind": "structure",
        "target": str(root),
        "profile": args.profile,
        "structure_status": structure_status(structure_findings),
        "source_manifest_contract": source_manifest_contract,
        "source_integrity": source_integrity,
        "scientific_readiness": "not_assessed",
        "scientific_validity": "not_determined_by_structure_audit",
        "counts": counts,
        "findings": findings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(f"AUDIT: {root} ({args.profile})")
        print(
            f"structure={report['structure_status'].upper()} "
            f"source_integrity={source_integrity.upper()} "
            "scientific_readiness=NOT_ASSESSED"
        )
        print(
            f"errors={counts['error']} warnings={counts['warning']} "
            f"info={counts['info']}"
        )
        for item in findings:
            print(
                f"[{item['level'].upper()}] {item['code']} | "
                f"{item['path']} | {item['message']}"
            )

    if counts["error"] or (args.strict and counts["warning"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
