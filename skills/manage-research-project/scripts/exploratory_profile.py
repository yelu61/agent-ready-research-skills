#!/usr/bin/env python3
"""Read-only structural checks for a small, explicitly exploratory project.

Only the four project-memory files are opened. Data, scripts and linked records
are not traversed. Findings describe recorded structure and freshness, never
whether an analysis ran or whether its scientific conclusions are correct.
"""

from __future__ import annotations

import os
import re
import stat
from datetime import date
from pathlib import Path


EXPLORATORY_FILES = ("README.md", "AGENTS.md", "CLAUDE.md", "PROJECT_NOTES.md")
PROFILE_MARKER = "<!-- research-project-profile: exploratory/v1 -->"
MAX_MEMORY_BYTES = 2 * 1024 * 1024
NOTE_SECTIONS = (
    "Question",
    "Inputs",
    "Actions and runs",
    "Observations",
    "Limits and decisions",
    "Next step",
)


def _issue(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def _read_memory(
    root: Path, names: tuple[str, ...]
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Read fixed root-level names without following symlinks or special files."""
    findings: list[dict[str, str]] = []
    texts: dict[str, str] = {}
    root = Path(root).expanduser()
    if not (
        hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
    ):
        return texts, [_issue(
            "error", "safe-read-unavailable", str(root),
            "Safe directory-relative reads require a supported POSIX runtime; use Linux, macOS or WSL.",
        )]
    try:
        if root.is_symlink():
            return texts, [_issue(
                "error", "path-symlink", str(root),
                "The project root must not be a symlink.",
            )]
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        return texts, [_issue("error", "root-read", str(root), str(exc))]
    try:
        for name in names:
            # Keep this reader limited to known flat names even for future callers.
            if name not in EXPLORATORY_FILES:
                findings.append(_issue("error", "path-unsafe", name, "Unknown memory file."))
                continue
            try:
                entry = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                if stat.S_ISLNK(entry.st_mode):
                    findings.append(_issue(
                        "error", "path-symlink", name,
                        "Project-memory files must not be symlinks; no target was read.",
                    ))
                    continue
                if not stat.S_ISREG(entry.st_mode):
                    findings.append(_issue(
                        "error", "file-type", name, "Expected a regular project-memory file.",
                    ))
                    continue
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
                with os.fdopen(fd, "rb") as handle:
                    opened = os.fstat(handle.fileno())
                    if not stat.S_ISREG(opened.st_mode):
                        findings.append(_issue(
                            "error", "file-type", name, "The entry changed to a non-regular file.",
                        ))
                        continue
                    if opened.st_nlink != 1:
                        findings.append(_issue(
                            "error", "path-hardlink", name,
                            "Memory files with hard-link aliases are not read; use an independent regular file.",
                        ))
                        continue
                    if opened.st_size > MAX_MEMORY_BYTES:
                        findings.append(_issue(
                            "error", "memory-file-too-large", name,
                            "Memory file exceeds the 2 MiB audit limit; retain history separately and link to it.",
                        ))
                        continue
                    content = handle.read(MAX_MEMORY_BYTES + 1)
                    if len(content) > MAX_MEMORY_BYTES:
                        findings.append(_issue(
                            "error", "memory-file-too-large", name,
                            "Memory file grew beyond the 2 MiB audit limit.",
                        ))
                        continue
                    texts[name] = content.decode("utf-8")
            except FileNotFoundError:
                findings.append(_issue(
                    "warning", "missing-file", name, "Exploratory project-memory file is missing.",
                ))
            except (OSError, UnicodeError) as exc:
                findings.append(_issue("error", "memory-read", name, str(exc)))
    finally:
        os.close(root_fd)
    return texts, findings


def is_exploratory(root: Path) -> bool:
    """Identify an explicit marker in a safely readable notes file.

    Callers deciding between profiles must give an existing formal project
    contract precedence; old exploratory notes may be retained as history.
    """
    texts, findings = _read_memory(root, ("PROJECT_NOTES.md",))
    if findings:
        return False
    return PROFILE_MARKER in texts["PROJECT_NOTES.md"].splitlines()


def audit_exploratory(root: Path, stale_days: int) -> list[dict[str, str]]:
    """Check memory presence, a declared profile, sections and update date only."""
    if not isinstance(stale_days, int) or isinstance(stale_days, bool) or stale_days < 0:
        raise ValueError("stale_days must be a non-negative integer")
    texts, findings = _read_memory(root, EXPLORATORY_FILES)
    notes = texts.get("PROJECT_NOTES.md")
    if notes is None:
        return findings
    if PROFILE_MARKER not in notes.splitlines():
        findings.append(_issue(
            "error", "exploratory-marker", "PROJECT_NOTES.md",
            "Expected the explicit exploratory/v1 profile marker; no profile was inferred from content.",
        ))
    for heading in NOTE_SECTIONS:
        pattern = rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)"
        match = re.search(pattern, notes, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if match is None or not match.group(1).strip():
            findings.append(_issue(
                "warning", "exploratory-note-section", "PROJECT_NOTES.md",
                f"Record '{heading}' or explicitly state that it is unknown/not yet done; content truth is not checked.",
            ))
    date_match = re.search(
        r"^(?:Last updated|Updated|更新日期)\s*:\s*(\S+)\s*$", notes, re.MULTILINE | re.IGNORECASE,
    )
    if date_match is None:
        findings.append(_issue(
            "warning", "missing-date", "PROJECT_NOTES.md", "No explicit Last updated date was recorded.",
        ))
    else:
        try:
            date_text = date_match.group(1)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
                raise ValueError("Use YYYY-MM-DD for Last updated.")
            updated = date.fromisoformat(date_text)
        except ValueError as exc:
            findings.append(_issue("warning", "invalid-date", "PROJECT_NOTES.md", str(exc)))
        else:
            age = (date.today() - updated).days
            if age < 0:
                findings.append(_issue(
                    "warning", "future-date", "PROJECT_NOTES.md", "Last updated is in the future.",
                ))
            elif age > stale_days:
                findings.append(_issue(
                    "warning", "stale-document", "PROJECT_NOTES.md",
                    f"Last updated {age} days ago; check whether the next step is still current. Do not change the date without reviewing the record.",
                ))
    return findings
