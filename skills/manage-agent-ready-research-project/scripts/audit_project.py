#!/usr/bin/env python3
"""Audit project memory, portability, staleness and manifest targets."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

from scaffold_project import profile_spec


EXCLUDED_PARTS = {".git", ".archive", "data/raw", "node_modules", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".r", ".R", ".sh", ".yaml", ".yml", ".toml"}
ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:/Users/|/home/|[A-Z]:\\\\)")


def issue(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


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
        if candidate.is_file():
            files.append(candidate)
        elif candidate.is_dir():
            files.extend(path for path in candidate.rglob("*") if path.is_file())
    for path in sorted(set(files)):
        if relative_parts(path, root) & EXCLUDED_PARTS:
            continue
        if path.suffix == ".ipynb":
            try:
                notebook = json.loads(path.read_text(encoding="utf-8"))
                text = "\n".join(
                    "".join(cell.get("source", []))
                    for cell in notebook.get("cells", [])
                    if cell.get("cell_type") == "code"
                )
            except Exception as exc:
                findings.append(
                    issue("warning", "notebook-json", str(path.relative_to(root)), str(exc))
                )
                continue
        elif path.suffix in TEXT_SUFFIXES or path.name in {"AGENTS.md", "CLAUDE.md"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        else:
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
    if not path.is_file():
        return None
    match = re.search(
        r"(?:Last updated|Updated|更新日期)\s*:\s*(\d{4}-\d{2}-\d{2})",
        path.read_text(encoding="utf-8"),
        re.IGNORECASE,
    )
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def check_manifest_targets(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in root.rglob("*MANIFEST.tsv"):
        if ".archive" in path.parts:
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
        except Exception as exc:
            findings.append(issue("error", "manifest-read", str(path.relative_to(root)), str(exc)))
            continue
        for row_number, row in enumerate(rows, start=2):
            for key, value in row.items():
                if not value or "path" not in key.lower():
                    continue
                for raw in value.split(";"):
                    target = raw.strip()
                    if not target or target.startswith(("http://", "https://", "TODO")):
                        continue
                    if any(token in target for token in ("[", "*", "{{")):
                        continue
                    if not (root / target).exists():
                        findings.append(
                            issue(
                                "warning",
                                "manifest-target",
                                str(path.relative_to(root)),
                                f"Row {row_number}, {key}: target not found: {target}",
                            )
                        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an agent-ready research project.")
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--profile", choices=["minimal", "research", "manuscript"], default="research"
    )
    parser.add_argument("--stale-days", type=int, default=30)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.target.expanduser().resolve()
    findings: list[dict[str, str]] = []
    if not root.is_dir():
        findings.append(issue("error", "missing-root", str(root), "Project directory does not exist."))
    else:
        _, required_files = profile_spec(args.profile)
        for relative in required_files:
            if not (root / relative).is_file():
                findings.append(
                    issue(
                        "warning",
                        "missing-file",
                        relative,
                        "Recommended project file is missing; document an accepted equivalent or scaffold it.",
                    )
                )

        agents = root / "AGENTS.md"
        if agents.is_file() and "data/raw" not in agents.read_text(encoding="utf-8"):
            findings.append(
                issue("warning", "raw-protection", "AGENTS.md", "Raw-data protection is not explicit.")
            )

        for relative in ("docs/PROJECT_STATUS.md", "docs/SESSION_HANDOFF.md"):
            path = root / relative
            updated = parse_last_updated(path)
            if path.is_file() and updated is None:
                findings.append(issue("warning", "missing-date", relative, "No parseable Last updated date."))
            elif updated and (date.today() - updated).days > args.stale_days:
                findings.append(
                    issue(
                        "warning",
                        "stale-document",
                        relative,
                        f"Last updated {(date.today() - updated).days} days ago.",
                    )
                )

        status = root / "docs/PROJECT_STATUS.md"
        if status.is_file() and "Next minimal executable task" not in status.read_text(encoding="utf-8"):
            findings.append(
                issue("warning", "next-task", str(status.relative_to(root)), "No next minimal executable task section.")
            )

        todo_count = 0
        for path in (root / "docs").glob("*.md") if (root / "docs").is_dir() else []:
            todo_count += len(re.findall(r"\bTODO:", path.read_text(encoding="utf-8")))
        if todo_count:
            findings.append(
                issue("info", "todo-count", "docs/", f"{todo_count} unresolved TODO placeholders.")
            )

        findings.extend(scan_absolute_paths(root))
        findings.extend(check_manifest_targets(root))

    counts = {
        level: sum(item["level"] == level for item in findings)
        for level in ("error", "warning", "info")
    }
    report = {
        "target": str(root),
        "profile": args.profile,
        "counts": counts,
        "findings": findings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"AUDIT: {root} ({args.profile})")
        print(f"errors={counts['error']} warnings={counts['warning']} info={counts['info']}")
        for item in findings:
            print(f"[{item['level'].upper()}] {item['code']} | {item['path']} | {item['message']}")

    if counts["error"] or (args.strict and counts["warning"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
