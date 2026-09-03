#!/usr/bin/env python3
"""Shared, standard-library helpers for project integrity contracts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
SOURCE_SCHEMA = "source-manifest/v1"
READINESS_SCHEMA = "research-readiness/v1"


class ContractError(ValueError):
    """Raised when a project contract cannot be checked safely."""


def cli_error(message: str, *, json_mode: bool, **context: Any) -> int:
    """Emit a stable post-parse CLI error, including JSON for machine callers."""
    if json_mode:
        print(
            json.dumps(
                {"status": "error", "error": message, **context},
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    return 2


def finding(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def load_json_object(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"Duplicate JSON object key: {key}")
            result[key] = value
        return result

    def reject_non_finite_constant(value: str) -> None:
        raise ContractError(f"Non-finite JSON number is not allowed: {value}")

    def parse_finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ContractError(f"Non-finite JSON number is not allowed: {value}")
        return parsed

    try:
        document = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite_constant,
            parse_float=parse_finite_float,
        )
    except ContractError as exc:
        raise ContractError(f"Cannot read JSON object {path}: {exc}") from exc
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError(f"Cannot read JSON object {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ContractError(f"Expected a JSON object in {path}")

    def reject_surrogates(value: Any) -> None:
        pending = [value]
        while pending:
            current = pending.pop()
            if isinstance(current, str):
                if any(
                    0xD800 <= ord(character) <= 0xDFFF for character in current
                ):
                    raise ContractError(
                        f"Cannot read JSON object {path}: string contains a lone Unicode surrogate"
                    )
            elif isinstance(current, list):
                pending.extend(current)
            elif isinstance(current, dict):
                pending.extend(current.keys())
                pending.extend(current.values())
            elif isinstance(current, float) and not math.isfinite(current):
                raise ContractError(
                    f"Cannot read JSON object {path}: non-finite number is not allowed"
                )

    reject_surrogates(document)
    return document


def parse_rfc3339(value: Any) -> datetime:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        raise ContractError("Expected a strict RFC 3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"Invalid RFC 3339 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ContractError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def resolve_project_relative(root: Path, raw: Any, *, must_exist: bool = False) -> Path:
    value = portable_project_relative(raw)
    relative = Path(value)

    root_resolved = root.resolve()
    candidate = root / relative
    current = root_resolved
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ContractError(f"Symlink path components are not allowed: {value}")
    try:
        candidate.resolve(strict=False).relative_to(root_resolved)
    except ValueError as exc:
        raise ContractError(f"Path resolves outside the project: {value}") from exc
    if must_exist and not candidate.exists():
        raise ContractError(f"Project path does not exist: {value}")
    return candidate


def portable_project_relative(raw: Any) -> str:
    """Validate and normalize a portable, project-relative POSIX path."""
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise ContractError("Project path must be a non-empty string")
    value = raw.strip()
    windows = PureWindowsPath(value)
    relative = Path(value)
    if relative.is_absolute() or windows.is_absolute() or windows.drive:
        raise ContractError(f"Absolute path is not allowed: {value}")
    if "\\" in value:
        raise ContractError(
            f"Backslashes are not allowed in portable project paths: {value}"
        )
    if ".." in relative.parts:
        raise ContractError(f"Parent traversal is not allowed: {value}")
    normalized = relative.as_posix()
    if not normalized:
        raise ContractError("Project path must not be empty")
    return normalized


def project_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ContractError(f"Path resolves outside the project: {path}") from exc


def sha256_regular_file(path: Path) -> tuple[str, int]:
    file_fd: int | None = None
    try:
        file_fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        before = os.fstat(file_fd)
    except OSError as exc:
        raise ContractError(f"Cannot safely open file {path}: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        os.close(file_fd)
        raise ContractError(f"Expected a regular file: {path}")

    digest = hashlib.sha256()
    try:
        with os.fdopen(file_fd, "rb") as handle:
            file_fd = None
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise ContractError(f"Cannot hash file {path}: {exc}") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)

    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ContractError(f"File changed while being hashed: {path}")
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ContractError(f"File changed while being hashed: {path}: {exc}") from exc
    if not stat.S_ISREG(current.st_mode) or any(
        getattr(after, field) != getattr(current, field) for field in stable_fields
    ):
        raise ContractError(f"File path changed while being hashed: {path}")
    return digest.hexdigest(), before.st_size


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def stable_source_id(relative: str, digest: str) -> str:
    identity = f"{relative}\0{digest}".encode("utf-8")
    return "SRC-" + hashlib.sha256(identity).hexdigest()[:16].upper()


def path_is_excluded(relative: str, excludes: list[str]) -> bool:
    candidate = Path(relative)
    for raw in excludes:
        excluded = Path(raw)
        if candidate == excluded or excluded in candidate.parents:
            return True
    return False


def collect_scope_files(
    root: Path, includes: list[str], excludes: list[str]
) -> dict[str, Path]:
    root = root.resolve()
    normalized_excludes = [portable_project_relative(raw) for raw in excludes]
    files: dict[str, Path] = {}
    for raw in includes:
        normalized_include = portable_project_relative(raw)
        included = resolve_project_relative(root, normalized_include, must_exist=True)
        if included.is_symlink():
            raise ContractError(f"Scope include cannot be a symlink: {raw}")
        if included.is_file():
            relative = project_relative(root, included)
            if not path_is_excluded(relative, normalized_excludes):
                files[relative] = included
            continue
        if not included.is_dir():
            raise ContractError(
                f"Scope include is not a regular file or directory: {raw}"
            )

        def walk_error(error: OSError) -> None:
            raise ContractError(f"Cannot traverse source scope {raw}: {error}")

        for directory, names, filenames in os.walk(
            included, topdown=True, followlinks=False, onerror=walk_error
        ):
            current = Path(directory)
            retained_names: list[str] = []
            for name in sorted(names):
                candidate = current / name
                lexical = candidate.relative_to(root).as_posix()
                if path_is_excluded(lexical, normalized_excludes):
                    continue
                if candidate.is_symlink():
                    raise ContractError(
                        f"Source scope contains a directory symlink: {lexical}"
                    )
                project_relative(root, candidate)
                retained_names.append(name)
            names[:] = retained_names
            for name in sorted(filenames):
                candidate = current / name
                lexical = candidate.relative_to(root).as_posix()
                if path_is_excluded(lexical, normalized_excludes):
                    continue
                if candidate.is_symlink():
                    raise ContractError(
                        f"Source scope contains a file symlink: {lexical}"
                    )
                relative = project_relative(root, candidate)
                if not candidate.is_file():
                    raise ContractError(
                        f"Source scope contains a non-regular entry: {relative}"
                    )
                files[relative] = candidate
    return dict(sorted(files.items()))


def validate_source_manifest_document(document: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    check_time = datetime.now(timezone.utc)
    allowed_top = {
        "schema_version",
        "generated_at",
        "scope_root",
        "scope_include",
        "scope_exclude",
        "hash_algorithm",
        "source_context",
        "entries",
    }
    for key in sorted(set(document) - allowed_top):
        findings.append(
            finding("error", "source-property", key, "Unexpected top-level property.")
        )
    if document.get("schema_version") != SOURCE_SCHEMA:
        findings.append(
            finding(
                "error", "source-schema", "schema_version", f"Expected {SOURCE_SCHEMA}."
            )
        )
    generated_at: datetime | None = None
    try:
        generated_at = parse_rfc3339(document.get("generated_at"))
    except ContractError as exc:
        findings.append(
            finding("error", "source-generated-at", "generated_at", str(exc))
        )
    if generated_at and generated_at > check_time + timedelta(minutes=5):
        findings.append(
            finding(
                "error",
                "source-generated-at-future",
                "generated_at",
                "Manifest generation time is in the future.",
            )
        )
    if document.get("scope_root") != ".":
        findings.append(
            finding(
                "error", "source-scope-root", "scope_root", "scope_root must be '.'."
            )
        )
    includes = document.get("scope_include")
    excludes = document.get("scope_exclude")
    if (
        not isinstance(includes, list)
        or not includes
        or not all(isinstance(item, str) for item in includes)
    ):
        findings.append(
            finding(
                "error",
                "source-includes",
                "scope_include",
                "Expected a non-empty string list.",
            )
        )
    else:
        if len(includes) != len(set(includes)):
            findings.append(
                finding(
                    "error",
                    "source-includes-duplicate",
                    "scope_include",
                    "Duplicate include paths are not allowed.",
                )
            )
        for index, raw in enumerate(includes):
            try:
                portable_project_relative(raw)
            except ContractError as exc:
                findings.append(
                    finding(
                        "error",
                        "source-include-path",
                        f"scope_include[{index}]",
                        str(exc),
                    )
                )
    if not isinstance(excludes, list) or not all(
        isinstance(item, str) for item in excludes
    ):
        findings.append(
            finding(
                "error", "source-excludes", "scope_exclude", "Expected a string list."
            )
        )
    else:
        if len(excludes) != len(set(excludes)):
            findings.append(
                finding(
                    "error",
                    "source-excludes-duplicate",
                    "scope_exclude",
                    "Duplicate exclude paths are not allowed.",
                )
            )
        for index, raw in enumerate(excludes):
            try:
                portable_project_relative(raw)
            except ContractError as exc:
                findings.append(
                    finding(
                        "error",
                        "source-exclude-path",
                        f"scope_exclude[{index}]",
                        str(exc),
                    )
                )
    if document.get("hash_algorithm") != "sha256":
        findings.append(
            finding(
                "error",
                "source-hash-algorithm",
                "hash_algorithm",
                "Only sha256 is supported.",
            )
        )

    context = document.get("source_context")
    if context is None:
        findings.append(
            finding(
                "error",
                "source-context",
                "source_context",
                "A source_context object is required.",
            )
        )
    else:
        allowed_context = {
            "source_system",
            "source_reference",
            "acquired_at",
            "data_freeze_id",
            "access_level",
            "subject_id_level",
            "license_or_agreement",
            "immutable_expected",
        }
        if not isinstance(context, dict):
            findings.append(
                finding(
                    "error", "source-context", "source_context", "Expected an object."
                )
            )
        else:
            for key in sorted(allowed_context - set(context)):
                findings.append(
                    finding(
                        "error",
                        "source-context-required",
                        f"source_context.{key}",
                        "Required property is missing.",
                    )
                )
            for key in sorted(set(context) - allowed_context):
                findings.append(
                    finding(
                        "error",
                        "source-context-property",
                        f"source_context.{key}",
                        "Unexpected property.",
                    )
                )
            if not isinstance(context.get("access_level"), str) or context.get(
                "access_level"
            ) not in {
                "public",
                "internal",
                "restricted",
                "controlled",
                "unknown",
            }:
                findings.append(
                    finding(
                        "error",
                        "source-access-level",
                        "source_context.access_level",
                        "Invalid access_level.",
                    )
                )
            if not isinstance(context.get("subject_id_level"), str) or context.get(
                "subject_id_level"
            ) not in {
                "none",
                "deidentified",
                "coded",
                "identifiable",
                "unknown",
            }:
                findings.append(
                    finding(
                        "error",
                        "source-subject-id-level",
                        "source_context.subject_id_level",
                        "Invalid subject_id_level.",
                    )
                )
            for key in (
                "source_system",
                "source_reference",
                "data_freeze_id",
                "license_or_agreement",
            ):
                if (
                    key in context
                    and context[key] is not None
                    and not isinstance(context[key], str)
                ):
                    findings.append(
                        finding(
                            "error",
                            "source-context-value",
                            f"source_context.{key}",
                            "Expected a string or null.",
                        )
                    )
            acquired_at: datetime | None = None
            if context.get("acquired_at") is not None:
                try:
                    acquired_at = parse_rfc3339(context["acquired_at"])
                except ContractError as exc:
                    findings.append(
                        finding(
                            "error",
                            "source-acquired-at",
                            "source_context.acquired_at",
                            str(exc),
                        )
                    )
            if acquired_at and acquired_at > check_time + timedelta(minutes=5):
                findings.append(
                    finding(
                        "error",
                        "source-acquired-at-future",
                        "source_context.acquired_at",
                        "Source acquisition time is in the future.",
                    )
                )
            if (
                acquired_at
                and generated_at
                and acquired_at > generated_at + timedelta(minutes=5)
            ):
                findings.append(
                    finding(
                        "error",
                        "source-time-order",
                        "source_context.acquired_at",
                        "Source acquisition time cannot be later than manifest generation time.",
                    )
                )
            if type(context.get("immutable_expected")) is not bool:
                findings.append(
                    finding(
                        "error",
                        "source-immutable-expected",
                        "source_context.immutable_expected",
                        "Expected a boolean.",
                    )
                )

    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        findings.append(
            finding(
                "error",
                "source-entries",
                "entries",
                "Expected at least one source entry.",
            )
        )
        return findings
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    allowed_entry = {
        "source_id",
        "path",
        "type",
        "size_bytes",
        "hash_status",
        "sha256",
        "access_reference",
    }
    for index, entry in enumerate(entries):
        location = f"entries[{index}]"
        if not isinstance(entry, dict):
            findings.append(
                finding("error", "source-entry", location, "Expected an object.")
            )
            continue
        for key in sorted(set(entry) - allowed_entry):
            findings.append(
                finding(
                    "error",
                    "source-entry-property",
                    f"{location}.{key}",
                    "Unexpected property.",
                )
            )
        source_id = entry.get("source_id")
        path = entry.get("path")
        if not isinstance(source_id, str) or not source_id:
            findings.append(
                finding("error", "source-id", location, "Missing source_id.")
            )
        elif not re.fullmatch(r"SRC-[0-9A-F]{16}", source_id):
            findings.append(
                finding(
                    "error",
                    "source-id",
                    location,
                    "source_id must use SRC- followed by 16 uppercase hexadecimal characters.",
                )
            )
        elif source_id in seen_ids:
            findings.append(
                finding(
                    "error",
                    "source-id-duplicate",
                    location,
                    f"Duplicate source_id: {source_id}",
                )
            )
        else:
            seen_ids.add(source_id)
        if not isinstance(path, str) or not path:
            findings.append(finding("error", "source-path", location, "Missing path."))
        elif path in seen_paths:
            findings.append(
                finding(
                    "error",
                    "source-path-duplicate",
                    location,
                    f"Duplicate path: {path}",
                )
            )
        else:
            seen_paths.add(path)
            try:
                portable_project_relative(path)
            except ContractError as exc:
                findings.append(
                    finding("error", "source-path-unsafe", location, str(exc))
                )
        if entry.get("type") != "file":
            findings.append(
                finding(
                    "error", "source-type", location, "Only file entries are supported."
                )
            )
        if type(entry.get("size_bytes")) is not int or entry.get("size_bytes", -1) < 0:
            findings.append(
                finding(
                    "error",
                    "source-size",
                    location,
                    "size_bytes must be a non-negative integer.",
                )
            )
        hash_status = entry.get("hash_status")
        if hash_status == "recorded":
            if not valid_sha256(entry.get("sha256")):
                findings.append(
                    finding(
                        "error",
                        "source-sha256",
                        location,
                        "recorded entries require a lowercase SHA-256.",
                    )
                )
            elif isinstance(path, str) and source_id != stable_source_id(
                path, entry["sha256"]
            ):
                findings.append(
                    finding(
                        "error",
                        "source-id-binding",
                        location,
                        "source_id does not match the path and recorded SHA-256.",
                    )
                )
        elif hash_status == "not_permitted":
            if not isinstance(entry.get("access_reference"), str) or not entry.get(
                "access_reference"
            ):
                findings.append(
                    finding(
                        "error",
                        "source-access-reference",
                        location,
                        "not_permitted entries require access_reference.",
                    )
                )
        else:
            findings.append(
                finding(
                    "error",
                    "source-hash-status",
                    location,
                    "hash_status must be recorded or not_permitted.",
                )
            )
    return findings


def verify_source_manifest_document(
    root: Path, document: dict[str, Any]
) -> dict[str, Any]:
    findings = validate_source_manifest_document(document)
    if any(item["level"] == "error" for item in findings):
        return _integrity_report(findings, manifest_contract_status="invalid")

    includes = document["scope_include"]
    excludes = document["scope_exclude"]
    try:
        actual = collect_scope_files(root, includes, excludes)
    except ContractError as exc:
        findings.append(finding("error", "source-scope", "scope_include", str(exc)))
        return _integrity_report(findings, manifest_contract_status="valid")

    expected = {entry["path"]: entry for entry in document["entries"]}
    for relative in sorted(expected):
        try:
            resolve_project_relative(root, relative)
        except ContractError as exc:
            findings.append(finding("error", "source-path-unsafe", relative, str(exc)))
    if any(item["level"] == "error" for item in findings):
        return _integrity_report(findings, manifest_contract_status="invalid")
    for relative in sorted(expected.keys() - actual.keys()):
        findings.append(
            finding("error", "source-missing", relative, "Manifest source is missing.")
        )
    for relative in sorted(actual.keys() - expected.keys()):
        findings.append(
            finding(
                "error",
                "source-unexpected",
                relative,
                "Unrecorded source exists inside the manifest scope.",
            )
        )

    for relative in sorted(expected.keys() & actual.keys()):
        entry = expected[relative]
        if entry.get("hash_status") == "not_permitted":
            findings.append(
                finding(
                    "warning",
                    "source-unverifiable",
                    relative,
                    "Source exists but policy does not permit checksum verification.",
                )
            )
            continue
        try:
            digest, size = sha256_regular_file(actual[relative])
        except ContractError as exc:
            findings.append(finding("error", "source-hash", relative, str(exc)))
            continue
        if size != entry.get("size_bytes"):
            findings.append(
                finding(
                    "error",
                    "source-size-changed",
                    relative,
                    f"Expected {entry.get('size_bytes')} bytes, found {size}.",
                )
            )
        if digest != entry.get("sha256"):
            findings.append(
                finding(
                    "error",
                    "source-hash-changed",
                    relative,
                    "SHA-256 does not match the recorded baseline.",
                )
            )
    return _integrity_report(findings, manifest_contract_status="valid")


def _integrity_report(
    findings: list[dict[str, str]], *, manifest_contract_status: str
) -> dict[str, Any]:
    counts = {
        level: sum(item["level"] == level for item in findings)
        for level in ("error", "warning", "info")
    }
    source_status = (
        "not_assessed"
        if manifest_contract_status == "invalid"
        else "fail"
        if counts["error"]
        else "review"
        if counts["warning"]
        else "pass"
    )
    legacy_status = "fail" if manifest_contract_status == "invalid" else source_status
    return {
        "manifest_contract_status": manifest_contract_status,
        "source_integrity_status": source_status,
        "integrity_status": legacy_status,
        "counts": counts,
        "findings": findings,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
