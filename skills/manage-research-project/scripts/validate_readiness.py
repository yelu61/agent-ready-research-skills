#!/usr/bin/env python3
"""Validate a domain readiness contract and detect stale project bindings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from project_contracts import (
    ContractError,
    READINESS_SCHEMA,
    cli_error,
    finding,
    load_json_object,
    parse_rfc3339,
    portable_project_relative,
    resolve_project_relative,
    sha256_regular_file,
    valid_sha256,
    verify_source_manifest_document,
)


POLICY_SCHEMA = "readiness-gate-policy/v1"
ANALYSIS_SPEC_SCHEMA = "research-analysis-spec/v1"
READINESS = {"ready", "review", "blocked"}
SOURCE_PROVENANCE_STATUS = {
    "verified",
    "unverified",
    "conflicting",
    "not_applicable",
}
ANALYSIS_MODE = {"descriptive", "exploratory", "confirmatory", "predictive", "causal"}
DATA_REQUIREMENT = {"none", "data_bearing"}
CLAIM_CLASS = {
    "observation",
    "association",
    "prediction",
    "causal_effect",
    "mechanism",
    "translational",
    "clinical_utility",
}
VALIDATION_LEVEL = {
    "none",
    "sensitivity",
    "orthogonal_same_material",
    "independent_external",
    "prospective",
}
LIFECYCLE = {"current", "superseded", "invalidated", "archived"}
GATE_STATUS = {"PASS", "FAIL", "UNKNOWN", "NA"}
EVIDENCE_KINDS = {"file", "artifact", "run", "decision", "external"}
CLAIM_AUTHORIZATION = {"authorized", "conditional", "not_authorized"}
PLACEHOLDER_RE = re.compile(
    r"^(?:(?:TODO|TBD)(?:\b|:)|(?:UNKNOWN|N/?A|NONE)$)", re.IGNORECASE
)

READINESS_KEYS = {
    "schema_version",
    "readiness_id",
    "analysis_id",
    "scope_id",
    "intended_use",
    "assessor",
    "assessed_at",
    "source_provenance_status",
    "readiness_status",
    "analysis_mode",
    "requested_claim_class",
    "achieved_validation_level",
    "claim_authorization",
    "lifecycle_status",
    "gate_policy",
    "analysis_spec",
    "input_manifest",
    "input_source_ids",
    "code_manifest",
    "environment_snapshot",
    "code_revision",
    "code_dirty",
    "backend_revision",
    "dependencies",
    "authorized_claim_classes",
    "prohibited_claim_classes",
    "claim_boundary_notes",
    "gates",
}
REQUIRED_READINESS_KEYS = READINESS_KEYS - {"dependencies"}
BINDING_KEYS = {"path", "sha256"}
GATE_KEYS = {
    "gate_id",
    "required_for_ready",
    "status",
    "requirement",
    "evidence",
    "impact",
    "remediation",
}
ARTIFACT_EVIDENCE_KEYS = {"kind", "ref", "path", "sha256", "record_sha256"}
RUN_EVIDENCE_KEYS = {
    "kind",
    "ref",
    "record_sha256",
    "log_sha256",
    "artifact_record_sha256s",
}
DECISION_EVIDENCE_KEYS = {"kind", "ref", "record_sha256"}
DESIGN_KEYS = {
    "population",
    "analysis_set",
    "exposure_or_intervention",
    "comparator",
    "outcome",
    "time_zero",
    "follow_up_window",
    "effect_measure",
    "unit_hierarchy",
    "missingness_and_censoring",
    "multiplicity_control",
    "decision_rule",
    "protocol_deviation_status",
}


def add_error(
    findings: list[dict[str, str]], code: str, path: str, message: str
) -> None:
    findings.append(finding("error", code, path, message))


def is_string_enum(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def is_concrete_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not PLACEHOLDER_RE.match(value.strip())
    )


def validate_keys(
    value: dict[str, Any],
    allowed: set[str],
    required: set[str],
    location: str,
    findings: list[dict[str, str]],
) -> None:
    for key in sorted(required - set(value)):
        add_error(
            findings,
            "readiness-required",
            f"{location}{key}",
            "Required property is missing.",
        )
    for key in sorted(set(value) - allowed):
        add_error(
            findings,
            "readiness-property",
            f"{location}{key}",
            "Unexpected property.",
        )


def require_string(
    document: dict[str, Any],
    key: str,
    findings: list[dict[str, str]],
    location: str = "",
) -> None:
    if not is_concrete_string(document.get(key)):
        add_error(
            findings,
            "readiness-string",
            f"{location}{key}",
            "Expected a concrete, non-placeholder string.",
        )


def require_enum(
    document: dict[str, Any],
    key: str,
    allowed: set[str],
    findings: list[dict[str, str]],
) -> None:
    if not is_string_enum(document.get(key), allowed):
        add_error(
            findings,
            f"readiness-{key.replace('_', '-')}",
            key,
            f"Expected one of {sorted(allowed)}.",
        )


def validate_string_list(
    value: Any,
    location: str,
    findings: list[dict[str, str]],
    *,
    allow_empty: bool,
    allowed_literals: set[str] | None = None,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        add_error(
            findings,
            "readiness-string-list",
            location,
            "Expected a string list.",
        )
        return []
    result: list[str] = []
    allowed_literals = allowed_literals or set()
    for index, item in enumerate(value):
        if not is_concrete_string(item) and not (
            isinstance(item, str) and item in allowed_literals
        ):
            add_error(
                findings,
                "readiness-string-list-item",
                f"{location}[{index}]",
                "Expected a concrete, non-placeholder string.",
            )
        else:
            result.append(item)
    if len(result) != len(set(result)):
        add_error(
            findings,
            "readiness-string-list-duplicate",
            location,
            "Duplicate values are not allowed.",
        )
    return result


def validate_binding(
    root: Path,
    value: Any,
    label: str,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> tuple[str, Path | None]:
    if not isinstance(value, dict):
        add_error(
            contract_findings,
            "readiness-binding",
            label,
            "Expected a path/SHA-256 object.",
        )
        return "invalid", None
    validate_keys(value, BINDING_KEYS, BINDING_KEYS, f"{label}.", contract_findings)
    raw_path = value.get("path")
    expected = value.get("sha256")
    if not valid_sha256(expected):
        add_error(
            contract_findings,
            "readiness-binding-sha256",
            f"{label}.sha256",
            "Expected a lowercase SHA-256.",
        )
    try:
        path = resolve_project_relative(root, raw_path)
    except ContractError as exc:
        add_error(
            contract_findings,
            "readiness-binding-path",
            f"{label}.path",
            str(exc),
        )
        return "invalid", None
    if not path.exists():
        add_error(
            currency_findings,
            "readiness-binding-missing",
            str(raw_path),
            f"{label} no longer exists.",
        )
        return "stale", path
    if path.is_symlink() or not path.is_file():
        add_error(
            contract_findings,
            "readiness-binding-type",
            str(raw_path),
            f"{label} must bind a regular, non-symlink file.",
        )
        return "invalid", path
    if not valid_sha256(expected):
        return "invalid", path
    try:
        observed, _ = sha256_regular_file(path)
    except ContractError as exc:
        currency_findings.append(
            finding(
                "warning",
                "readiness-binding-unverifiable",
                str(raw_path),
                str(exc),
            )
        )
        return "unknown", path
    if observed != expected:
        add_error(
            currency_findings,
            "readiness-binding-stale",
            str(raw_path),
            f"{label} SHA-256 no longer matches.",
        )
        return "stale", path
    return "current", path


def registry_row(
    root: Path,
    registry_path: str,
    id_column: str,
    reference: str,
    location: str,
    findings: list[dict[str, str]],
) -> dict[str, str] | None:
    """Resolve one unique registry ID without treating a free string as evidence."""
    try:
        path = resolve_project_relative(root, registry_path, must_exist=True)
    except ContractError as exc:
        add_error(findings, "readiness-evidence-registry", location, str(exc))
        return None
    if path.is_symlink() or not path.is_file():
        add_error(
            findings,
            "readiness-evidence-registry-type",
            location,
            f"Evidence registry must be a regular, non-symlink file: {registry_path}",
        )
        return None
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None or id_column not in reader.fieldnames:
                raise ContractError(f"Registry lacks required column {id_column}")
            rows = list(reader)
            if any(not isinstance(name, str) or not name for name in reader.fieldnames):
                raise ContractError("Registry has a blank or invalid header")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ContractError("Registry has duplicate headers")
            if any(
                None in row
                or any(not isinstance(value, str) for value in row.values())
                for row in rows
            ):
                raise ContractError("Registry row width does not match its header")
    except (OSError, UnicodeError, csv.Error, ContractError) as exc:
        add_error(
            findings,
            "readiness-evidence-registry",
            location,
            f"Cannot read {registry_path}: {exc}",
        )
        return None
    matches = [row for row in rows if row.get(id_column) == reference]
    if len(matches) != 1:
        add_error(
            findings,
            "readiness-evidence-registry-closure",
            location,
            f"Expected one {id_column}={reference!r} in {registry_path}; found {len(matches)}.",
        )
        return None
    return matches[0]


def validate_readiness_id_uniqueness(
    root: Path, readiness_id: Any, findings: list[dict[str, str]]
) -> None:
    """Require one readiness identity across the active readiness registry."""
    if not is_concrete_string(readiness_id):
        return
    try:
        directory = resolve_project_relative(root, "analysis/readiness")
    except ContractError as exc:
        add_error(findings, "readiness-registry", "analysis/readiness", str(exc))
        return
    if not directory.exists():
        return
    if directory.is_symlink() or not directory.is_dir():
        add_error(
            findings,
            "readiness-registry",
            "analysis/readiness",
            "Readiness registry must be a regular project directory.",
        )
        return
    matches: list[str] = []
    for path in sorted(directory.glob("*.json")):
        relative = path.relative_to(root).as_posix()
        try:
            safe_path = resolve_project_relative(root, relative, must_exist=True)
            candidate = load_json_object(safe_path)
        except ContractError as exc:
            add_error(findings, "readiness-registry-read", relative, str(exc))
            continue
        if candidate.get("readiness_id") == readiness_id:
            matches.append(relative)
    if len(matches) != 1:
        add_error(
            findings,
            "readiness-id-duplicate",
            "readiness_id",
            f"Expected one active readiness record with this ID; found {len(matches)}: {matches}",
        )


def parse_registry_ids(
    value: Any,
    location: str,
    findings: list[dict[str, str]],
    *,
    allow_empty: bool = False,
) -> list[str]:
    """Parse the contract's semicolon-delimited stable-ID fields."""
    if allow_empty and value == "":
        return []
    if not is_concrete_string(value):
        add_error(
            findings,
            "readiness-registry-ids",
            location,
            "Expected one or more semicolon-delimited artifact IDs.",
        )
        return []
    values = [item.strip() for item in value.split(";")]
    if any(not re.fullmatch(r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", item) for item in values):
        add_error(
            findings,
            "readiness-registry-ids",
            location,
            "Artifact IDs must use ART-* syntax and semicolon delimiters.",
        )
    if len(values) != len(set(values)):
        add_error(
            findings,
            "readiness-registry-ids-duplicate",
            location,
            "Duplicate artifact IDs are not allowed.",
        )
    return values


def parse_source_ids(
    value: Any,
    location: str,
    findings: list[dict[str, str]],
    *,
    allow_empty: bool,
) -> list[str]:
    """Parse semicolon-delimited source IDs propagated through artifacts."""
    if allow_empty and value == "":
        return []
    if not is_concrete_string(value):
        add_error(
            findings,
            "readiness-artifact-source-ids",
            location,
            "Expected one or more semicolon-delimited source IDs.",
        )
        return []
    values = [item.strip() for item in value.split(";")]
    if any(not re.fullmatch(r"SRC-[0-9A-F]{16}", item) for item in values):
        add_error(
            findings,
            "readiness-artifact-source-ids",
            location,
            "Source IDs must use SRC-* syntax and semicolon delimiters.",
        )
    if len(values) != len(set(values)):
        add_error(
            findings,
            "readiness-artifact-source-ids-duplicate",
            location,
            "Duplicate source IDs are not allowed.",
        )
    return values


def validate_artifact_row(
    root: Path,
    row: dict[str, str],
    location: str,
    expected_analysis_id: Any,
    data_requirement: Any,
    expected_source_ids: list[str],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> list[str]:
    """Validate the minimum machine-usable ARTIFACTS.tsv row contract."""
    for field in ("artifact_id", "analysis_id", "path", "role", "recorded_at"):
        if not is_concrete_string(row.get(field)):
            add_error(
                contract_findings,
                "readiness-artifact-row-incomplete",
                location,
                f"Artifact registry row requires concrete {field}.",
            )
    if not isinstance(row.get("artifact_id"), str) or not re.fullmatch(
        r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", row["artifact_id"]
    ):
        add_error(
            contract_findings,
            "readiness-artifact-id",
            location,
            "Artifact IDs must use ART-* syntax.",
        )
    if row.get("analysis_id") != expected_analysis_id:
        add_error(
            contract_findings,
            "readiness-evidence-artifact-analysis",
            location,
            "Artifact evidence belongs to a different analysis_id.",
        )
    expected_source_status = (
        "verified"
        if data_requirement == "data_bearing"
        else "not_applicable"
        if data_requirement == "none"
        else None
    )
    if expected_source_status is not None and row.get(
        "source_provenance_status"
    ) != expected_source_status:
        add_error(
            contract_findings,
            "readiness-artifact-source-provenance",
            location,
            "Artifact source provenance does not match the analysis data requirement; "
            f"expected {expected_source_status}.",
        )
    artifact_source_ids = parse_source_ids(
        row.get("source_ids"),
        f"{location}.source_ids",
        contract_findings,
        allow_empty=data_requirement == "none",
    )
    if data_requirement == "data_bearing":
        outside_scope = sorted(set(artifact_source_ids) - set(expected_source_ids))
        if outside_scope:
            add_error(
                contract_findings,
                "readiness-artifact-source-scope",
                f"{location}.source_ids",
                f"Artifact cites source IDs outside the assessed source set: {outside_scope}.",
            )
    elif data_requirement == "none" and artifact_source_ids:
        add_error(
            contract_findings,
            "readiness-artifact-source-not-applicable",
            f"{location}.source_ids",
            "A data-free analysis artifact cannot cite source IDs.",
        )
    if row.get("access_class") not in {
        "public",
        "internal",
        "restricted",
        "controlled",
    }:
        add_error(
            contract_findings,
            "readiness-artifact-access-class",
            location,
            "Artifact registry row has an invalid access_class.",
        )
    if row.get("access_class") in {"restricted", "controlled"} and not is_concrete_string(
        row.get("license_or_agreement")
    ):
        add_error(
            contract_findings,
            "readiness-artifact-access-governance",
            location,
            "Restricted/controlled artifacts require a license or agreement reference.",
        )
    if row.get("lifecycle_status") != "current":
        add_error(
            currency_findings,
            "readiness-evidence-artifact-lifecycle",
            location,
            "Readiness evidence artifact is not current.",
        )
    try:
        recorded_at = parse_rfc3339(row.get("recorded_at"))
    except ContractError as exc:
        add_error(
            contract_findings,
            "readiness-evidence-artifact-time",
            location,
            f"Invalid artifact recorded_at: {exc}",
        )
    else:
        if assessed_at and recorded_at > assessed_at + timedelta(minutes=5):
            add_error(
                contract_findings,
                "readiness-evidence-artifact-after-assessment",
                location,
                "Artifact evidence was recorded after the readiness assessment.",
            )
    status, artifact_path = validate_binding(
        root,
        {"path": row.get("path"), "sha256": row.get("sha256")},
        f"{location}.artifact",
        contract_findings,
        currency_findings,
    )
    try:
        expected_size = int(row.get("size_bytes", ""))
    except ValueError:
        expected_size = -1
    if expected_size < 0:
        add_error(
            contract_findings,
            "readiness-artifact-size",
            location,
            "Artifact size_bytes must be a non-negative integer.",
        )
    elif status == "current" and artifact_path is not None:
        try:
            actual_size = artifact_path.stat().st_size
        except OSError as exc:
            add_error(currency_findings, "readiness-artifact-size", location, str(exc))
        else:
            if actual_size != expected_size:
                add_error(
                    currency_findings,
                    "readiness-artifact-size-stale",
                    location,
                    f"Artifact size changed from {expected_size} to {actual_size} bytes.",
                )
    return artifact_source_ids


def valid_external_reference(value: str) -> bool:
    """Accept canonical DOI URLs or the assigned-name portion of RFC 8141 URNs."""
    uri_component = r"(?:[A-Za-z0-9._~!$&'()*+,;=:@/-]|%[0-9A-Fa-f]{2})+"

    def component_is_safe(component: str) -> bool:
        if re.fullmatch(uri_component, component) is None:
            return False
        encoded_octets = (
            int(match.group(1), 16)
            for match in re.finditer(r"%([0-9A-Fa-f]{2})", component)
        )
        return not any(octet < 0x20 or octet == 0x7F for octet in encoded_octets)

    if any(character.isspace() for character in value):
        return False
    urn_match = re.fullmatch(
        r"[Uu][Rr][Nn]:(?P<nid>[A-Za-z0-9](?:[A-Za-z0-9-]{0,30}[A-Za-z0-9])):(?P<nss>.+)",
        value,
    )
    if urn_match is not None:
        return component_is_safe(urn_match.group("nss"))
    if not value.startswith("https://doi.org/"):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme != "https"
        or parsed.netloc != "doi.org"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        return False
    doi_match = re.fullmatch(
        r"/10\.\d{4,9}/(?P<suffix>.+)",
        parsed.path,
    )
    return bool(
        doi_match is not None
        and component_is_safe(doi_match.group("suffix"))
    )


def canonical_record_sha256(value: dict[str, str] | str) -> str:
    """Hash one row or section without binding unrelated registry records."""
    if isinstance(value, dict):
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    else:
        payload = value.strip() + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_provenance_gaps(manifest: dict[str, Any]) -> list[str]:
    """Return missing identity metadata needed to declare source provenance verified."""
    context = manifest.get("source_context")
    if not isinstance(context, dict):
        return ["source_context"]
    gaps: list[str] = []
    for key in ("source_system", "source_reference", "data_freeze_id"):
        if not is_concrete_string(context.get(key)):
            gaps.append(key)
    try:
        parse_rfc3339(context.get("acquired_at"))
    except ContractError:
        gaps.append("acquired_at")
    if context.get("access_level") == "unknown":
        gaps.append("access_level")
    if context.get("subject_id_level") == "unknown":
        gaps.append("subject_id_level")
    if (
        context.get("access_level") in {"restricted", "controlled"}
        or context.get("subject_id_level") in {"coded", "identifiable"}
    ) and not is_concrete_string(context.get("license_or_agreement")):
        gaps.append("license_or_agreement")
    return gaps


def validate_evidence_list(
    root: Path,
    value: Any,
    location: str,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
    *,
    allow_empty: bool,
    gate_status: Any,
    analysis_id: Any,
    scope_id: Any,
    assessed_at: datetime | None,
    analysis_spec_binding: Any,
    environment_snapshot_binding: Any,
    code_revision: Any,
    code_dirty: Any,
    backend_revision: Any,
    entry_points: list[str],
    data_requirement: Any,
    input_source_ids: list[str],
) -> list[dict[str, Any]]:
    """Validate typed evidence identity and local reference closure, not truth."""
    if not isinstance(value, list) or (not allow_empty and not value):
        add_error(
            contract_findings,
            "readiness-evidence-list",
            location,
            "Expected a list of typed evidence references.",
        )
        return []

    validated: list[dict[str, Any]] = []
    signatures: list[str] = []
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            add_error(
                contract_findings,
                "readiness-evidence-item",
                item_location,
                "Expected an evidence object with kind and ref.",
            )
            continue
        kind = item.get("kind")
        if kind == "file":
            required = {"kind", "ref", "sha256"}
            allowed = {"kind", "ref", "sha256"}
        elif kind == "artifact":
            required = ARTIFACT_EVIDENCE_KEYS
            allowed = ARTIFACT_EVIDENCE_KEYS
        elif kind == "run":
            required = RUN_EVIDENCE_KEYS
            allowed = RUN_EVIDENCE_KEYS
        elif kind == "decision":
            required = DECISION_EVIDENCE_KEYS
            allowed = DECISION_EVIDENCE_KEYS
        else:
            required = {"kind", "ref"}
            allowed = {"kind", "ref"}
        validate_keys(item, allowed, required, f"{item_location}.", contract_findings)
        reference = item.get("ref")
        if not is_string_enum(kind, EVIDENCE_KINDS):
            add_error(
                contract_findings,
                "readiness-evidence-kind",
                f"{item_location}.kind",
                f"Expected one of {sorted(EVIDENCE_KINDS)}.",
            )
            continue
        if not is_concrete_string(reference):
            add_error(
                contract_findings,
                "readiness-evidence-ref",
                f"{item_location}.ref",
                "Expected a concrete, non-placeholder evidence reference.",
            )
            continue
        reference = reference.strip()
        if isinstance(kind, str) and kind in {
            "artifact",
            "run",
            "decision",
        } and not valid_sha256(
            item.get("record_sha256")
        ):
            add_error(
                contract_findings,
                "readiness-evidence-record-sha256",
                f"{item_location}.record_sha256",
                "Expected a lowercase SHA-256 for the referenced record.",
            )

        if kind == "file":
            validate_binding(
                root,
                {"path": reference, "sha256": item.get("sha256")},
                item_location,
                contract_findings,
                currency_findings,
            )
        elif kind == "artifact":
            if not re.fullmatch(r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", reference):
                add_error(
                    contract_findings,
                    "readiness-evidence-artifact-id",
                    f"{item_location}.ref",
                    "Artifact evidence IDs must use ART-* syntax.",
                )
            row = registry_row(
                root,
                "provenance/ARTIFACTS.tsv",
                "artifact_id",
                reference,
                item_location,
                contract_findings,
            )
            if row is not None:
                if item.get("record_sha256") != canonical_record_sha256(row):
                    add_error(
                        contract_findings,
                        "readiness-evidence-artifact-record-stale",
                        f"{item_location}.record_sha256",
                        "Evidence digest does not match the current ARTIFACTS.tsv row.",
                    )
                validate_artifact_row(
                    root,
                    row,
                    item_location,
                    analysis_id,
                    data_requirement,
                    input_source_ids,
                    assessed_at,
                    contract_findings,
                    currency_findings,
                )
                artifact_path = row.get("path")
                artifact_sha256 = row.get("sha256")
                if item.get("path") != artifact_path:
                    add_error(
                        contract_findings,
                        "readiness-evidence-artifact-mismatch",
                        f"{item_location}.path",
                        "Evidence path does not match the artifact registry.",
                    )
                if item.get("sha256") != artifact_sha256:
                    add_error(
                        contract_findings,
                        "readiness-evidence-artifact-mismatch",
                        f"{item_location}.sha256",
                        "Evidence SHA-256 does not match the artifact registry.",
                    )
        elif kind == "run":
            if not re.fullmatch(r"RUN-[A-Za-z0-9][A-Za-z0-9._-]*", reference):
                add_error(
                    contract_findings,
                    "readiness-evidence-run-id",
                    f"{item_location}.ref",
                    "Run evidence IDs must use RUN-* syntax.",
                )
            if not valid_sha256(item.get("log_sha256")):
                add_error(
                    contract_findings,
                    "readiness-evidence-run-log-sha256",
                    f"{item_location}.log_sha256",
                    "Expected a lowercase SHA-256 for the assessed run log.",
                )
            artifact_record_sha256s = item.get("artifact_record_sha256s")
            if not isinstance(artifact_record_sha256s, dict):
                add_error(
                    contract_findings,
                    "readiness-evidence-run-artifact-records",
                    f"{item_location}.artifact_record_sha256s",
                    "Expected an artifact-ID to record-SHA-256 object.",
                )
                artifact_record_sha256s = {}
            else:
                for artifact_id, digest in artifact_record_sha256s.items():
                    if not isinstance(artifact_id, str) or not re.fullmatch(
                        r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", artifact_id
                    ):
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-artifact-record-id",
                            f"{item_location}.artifact_record_sha256s",
                            "Artifact record-map keys must use ART-* syntax.",
                        )
                    if not valid_sha256(digest):
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-artifact-record-sha256",
                            f"{item_location}.artifact_record_sha256s.{artifact_id}",
                            "Expected a lowercase artifact-row SHA-256.",
                        )
            row = registry_row(
                root,
                "provenance/RUNS.tsv",
                "run_id",
                reference,
                item_location,
                contract_findings,
            )
            if row is not None and item.get(
                "record_sha256"
            ) != canonical_record_sha256(row):
                add_error(
                    contract_findings,
                    "readiness-evidence-run-record-stale",
                    f"{item_location}.record_sha256",
                    "Evidence digest does not match the current RUNS.tsv row.",
                )
            if row is not None and row.get("analysis_id") != analysis_id:
                add_error(
                    contract_findings,
                    "readiness-evidence-run-analysis",
                    item_location,
                    "Run evidence belongs to a different analysis_id.",
                )
            if (
                row is not None
                and is_string_enum(gate_status, {"PASS", "NA"})
                and row.get("execution_status") != "completed"
            ):
                add_error(
                    currency_findings,
                    "readiness-evidence-run-execution",
                    item_location,
                    "PASS/NA run evidence is not completed in RUNS.tsv.",
                )
            if row is not None and is_string_enum(gate_status, {"PASS", "NA"}):
                run_expectations = {
                    "implementation_status": "implemented",
                    "execution_status": "completed",
                    "analysis_spec_path": (
                        analysis_spec_binding.get("path")
                        if isinstance(analysis_spec_binding, dict)
                        else None
                    ),
                    "analysis_spec_sha256": (
                        analysis_spec_binding.get("sha256")
                        if isinstance(analysis_spec_binding, dict)
                        else None
                    ),
                    "code_revision": code_revision,
                    "code_dirty": (
                        str(code_dirty).lower() if type(code_dirty) is bool else None
                    ),
                    "backend_revision": backend_revision or "",
                    "environment_ref": (
                        environment_snapshot_binding.get("path")
                        if isinstance(environment_snapshot_binding, dict)
                        else None
                    ),
                    "exit_code": "0",
                }
                for field, expected in run_expectations.items():
                    if expected is not None and row.get(field) != expected:
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-context",
                            item_location,
                            f"Run {field} does not match the assessed execution context.",
                        )
                if row.get("entry_point") not in entry_points:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-entry-point",
                        item_location,
                        "Run entry_point is absent from the bound analysis specification.",
                    )
                config_path = row.get("config_path")
                config_sha256 = row.get("config_sha256")
                if config_path == "not_applicable":
                    if config_sha256:
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-config",
                            item_location,
                            "config_sha256 must be empty when config_path is not_applicable.",
                        )
                elif not is_concrete_string(config_path):
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-config",
                        item_location,
                        "PASS/NA run evidence requires a hash-bound config_path or "
                        "the literal not_applicable.",
                    )
                else:
                    validate_binding(
                        root,
                        {"path": config_path, "sha256": config_sha256},
                        f"{item_location}.configuration",
                        contract_findings,
                        currency_findings,
                    )
                for field in (
                    "validation_kind",
                    "validation_scope",
                    "validation_criterion",
                    "validation_evidence_ids",
                    "output_artifact_ids",
                    "log_path",
                ):
                    if not is_concrete_string(row.get(field)):
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-incomplete",
                            item_location,
                            f"PASS/NA run evidence requires concrete {field}.",
                        )
                artifact_id_sets = {
                    "input_artifact_ids": parse_registry_ids(
                        row.get("input_artifact_ids"),
                        f"{item_location}.input_artifact_ids",
                        contract_findings,
                        allow_empty=data_requirement == "none",
                    ),
                    "output_artifact_ids": parse_registry_ids(
                        row.get("output_artifact_ids"),
                        f"{item_location}.output_artifact_ids",
                        contract_findings,
                    ),
                    "validation_evidence_ids": parse_registry_ids(
                        row.get("validation_evidence_ids"),
                        f"{item_location}.validation_evidence_ids",
                        contract_findings,
                    ),
                }
                overlap = set(artifact_id_sets["input_artifact_ids"]) & set(
                    artifact_id_sets["output_artifact_ids"]
                )
                if overlap:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-lineage-cycle",
                        item_location,
                        f"Run input and output artifact IDs overlap: {sorted(overlap)}",
                    )
                expected_artifact_ids = set().union(*artifact_id_sets.values())
                if set(artifact_record_sha256s) != expected_artifact_ids:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-artifact-records",
                        f"{item_location}.artifact_record_sha256s",
                        "Artifact record-map keys must exactly match the union of run "
                        f"input/output/validation IDs: {sorted(expected_artifact_ids)}.",
                    )
                artifact_source_sets = {field: set() for field in artifact_id_sets}
                artifact_paths = {field: set() for field in artifact_id_sets}
                expected_input_ids = set(artifact_id_sets["input_artifact_ids"])
                for field, artifact_ids in artifact_id_sets.items():
                    for artifact_id in artifact_ids:
                        artifact_row = registry_row(
                            root,
                            "provenance/ARTIFACTS.tsv",
                            "artifact_id",
                            artifact_id,
                            f"{item_location}.{field}",
                            contract_findings,
                        )
                        if artifact_row is None:
                            continue
                        if artifact_record_sha256s.get(
                            artifact_id
                        ) != canonical_record_sha256(artifact_row):
                            add_error(
                                contract_findings,
                                "readiness-evidence-run-artifact-record-stale",
                                f"{item_location}.artifact_record_sha256s.{artifact_id}",
                                "Assessed artifact-row digest no longer matches the registry.",
                            )
                        artifact_source_sets[field].update(
                            validate_artifact_row(
                                root,
                                artifact_row,
                                f"{item_location}.{field}.{artifact_id}",
                                analysis_id,
                                data_requirement,
                                input_source_ids,
                                assessed_at,
                                contract_findings,
                                currency_findings,
                            )
                        )
                        try:
                            artifact_paths[field].add(
                                portable_project_relative(artifact_row.get("path"))
                            )
                        except ContractError:
                            pass
                        if (
                            field == "output_artifact_ids"
                            and artifact_row.get("run_id") != reference
                        ):
                            add_error(
                                contract_findings,
                                "readiness-evidence-run-output-lineage",
                                item_location,
                                f"Output artifact {artifact_id} does not bind run {reference}.",
                            )
                        if field == "output_artifact_ids":
                            parent_ids = parse_registry_ids(
                                artifact_row.get("parent_artifact_ids"),
                                f"{item_location}.{field}.{artifact_id}.parent_artifact_ids",
                                contract_findings,
                                allow_empty=not expected_input_ids,
                            )
                            if set(parent_ids) != expected_input_ids:
                                add_error(
                                    contract_findings,
                                    "readiness-evidence-run-parent-lineage",
                                    item_location,
                                    f"Output artifact {artifact_id} parent IDs must exactly "
                                    "match the run input IDs.",
                                )
                overlapping_paths = (
                    artifact_paths["input_artifact_ids"]
                    & artifact_paths["output_artifact_ids"]
                )
                if overlapping_paths:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-path-overlap",
                        item_location,
                        "Run inputs and outputs must not resolve to the same registered "
                        f"paths: {sorted(overlapping_paths)}.",
                    )
                if data_requirement == "data_bearing":
                    assessed_sources = set(input_source_ids)
                    run_input_sources = artifact_source_sets["input_artifact_ids"]
                    if not run_input_sources:
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-source-lineage",
                            f"{item_location}.input_artifact_ids",
                            "A data-bearing run must close to at least one input source ID.",
                        )
                    outside_scope = sorted(run_input_sources - assessed_sources)
                    if outside_scope:
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-source-lineage",
                            f"{item_location}.input_artifact_ids",
                            "Run input source IDs are outside the assessed source set: "
                            f"{outside_scope}.",
                        )
                    for field in ("output_artifact_ids", "validation_evidence_ids"):
                        observed_sources = artifact_source_sets[field]
                        if observed_sources != run_input_sources:
                            add_error(
                                contract_findings,
                                "readiness-evidence-run-source-lineage",
                                f"{item_location}.{field}",
                                "Run output/validation source IDs must collectively equal "
                                "that run's input source IDs: "
                                f"{sorted(run_input_sources)}.",
                            )
                try:
                    log_relative = portable_project_relative(row.get("log_path"))
                    expected_log_parent = Path("analysis") / "runs" / reference
                    if expected_log_parent not in Path(log_relative).parents:
                        raise ContractError(
                            "Run log must be inside analysis/runs/<run_id>/"
                        )
                    log_path = resolve_project_relative(
                        root, log_relative, must_exist=True
                    )
                    if log_path.is_symlink() or not log_path.is_file():
                        raise ContractError("Run log must be a regular non-symlink file")
                    if log_path.stat().st_size == 0:
                        raise ContractError("Run log must not be empty")
                    observed_log_sha256, _ = sha256_regular_file(log_path)
                    if (
                        valid_sha256(item.get("log_sha256"))
                        and observed_log_sha256 != item.get("log_sha256")
                    ):
                        add_error(
                            currency_findings,
                            "readiness-evidence-run-log-stale",
                            item_location,
                            "Run log SHA-256 no longer matches the assessed log.",
                        )
                except (ContractError, OSError) as exc:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-log",
                        item_location,
                        str(exc),
                    )
                technical_status = row.get("technical_validation_status")
                if technical_status is None:
                    technical_status = row.get("validation_status")
                if technical_status != "passed":
                    add_error(
                        currency_findings,
                        "readiness-evidence-run-validation",
                        item_location,
                        "PASS/NA run evidence lacks passed technical validation.",
                    )
                started_at: datetime | None = None
                completed_at: datetime | None = None
                for field in ("started_at", "completed_at"):
                    try:
                        parsed = parse_rfc3339(row.get(field))
                    except ContractError as exc:
                        add_error(
                            contract_findings,
                            "readiness-evidence-run-time",
                            item_location,
                            f"Invalid run {field}: {exc}",
                        )
                    else:
                        if field == "started_at":
                            started_at = parsed
                        else:
                            completed_at = parsed
                if started_at and completed_at and started_at > completed_at:
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-time-order",
                        item_location,
                        "Run start time is later than completion time.",
                    )
                if (
                    completed_at
                    and assessed_at
                    and completed_at > assessed_at + timedelta(minutes=5)
                ):
                    add_error(
                        contract_findings,
                        "readiness-evidence-run-after-assessment",
                        item_location,
                        "Run evidence completed after the readiness assessment.",
                    )
        elif kind == "decision":
            if not re.fullmatch(r"D-\d{8}-\d{2,}", reference):
                add_error(
                    contract_findings,
                    "readiness-evidence-decision-id",
                    f"{item_location}.ref",
                    "Expected a decision ID such as D-20260902-01.",
                )
            else:
                try:
                    decision_log = resolve_project_relative(
                        root, "docs/DECISION_LOG.md", must_exist=True
                    )
                    if decision_log.is_symlink() or not decision_log.is_file():
                        raise ContractError(
                            "Decision log must be a regular, non-symlink file"
                        )
                    text = decision_log.read_text(encoding="utf-8")
                    matches = re.findall(
                        rf"(?ms)^(?P<section>###\s+{re.escape(reference)}\s+(?:—|-)\s+.*?)(?=^###\s|\Z)",
                        text,
                    )
                    if len(matches) != 1:
                        raise ContractError(
                            f"Expected one decision heading for {reference}; found {len(matches)}"
                        )
                    section = matches[0]
                    if item.get("record_sha256") != canonical_record_sha256(section):
                        raise ContractError(
                            "Evidence digest does not match the current decision section"
                        )
                    identity_matches = re.findall(
                        r"(?m)^-\s+Analysis/claim/scope IDs:\s*(?P<ids>.+?)\s*$",
                        section,
                    )
                    if len(identity_matches) != 1:
                        raise ContractError(
                            "Decision requires exactly one Analysis/claim/scope IDs field"
                        )
                    identifiers = identity_matches[0]
                    bound = any(
                        isinstance(expected, str)
                        and bool(expected)
                        and re.search(
                            rf"(?<![A-Za-z0-9_-]){re.escape(expected)}(?![A-Za-z0-9_-])",
                            identifiers,
                        )
                        for expected in (analysis_id, scope_id)
                    )
                    if not bound:
                        raise ContractError(
                            "Decision is not bound to this analysis_id or scope_id"
                        )
                    for label in ("Decision", "Evidence/source", "Reason"):
                        field_matches = re.findall(
                            rf"(?m)^-\s+{re.escape(label)}:\s*(.+?)\s*$",
                            section,
                        )
                        if len(field_matches) != 1 or not is_concrete_string(
                            field_matches[0]
                        ):
                            raise ContractError(
                                f"Decision requires exactly one concrete {label} field"
                            )
                    id_date = datetime.strptime(reference[2:10], "%Y%m%d").date()
                    date_matches = re.findall(
                        r"(?m)^-\s+Date:\s*(\d{4}-\d{2}-\d{2})\s*$",
                        section,
                    )
                    if len(date_matches) != 1:
                        raise ContractError(
                            "Decision requires exactly one parseable Date field"
                        )
                    decision_date = datetime.strptime(date_matches[0], "%Y-%m-%d").date()
                    if decision_date != id_date:
                        raise ContractError(
                            "Decision Date does not match the date encoded in its ID"
                        )
                    if assessed_at and decision_date > assessed_at.date():
                        raise ContractError(
                            "Decision evidence is dated after the readiness assessment"
                        )
                except (ContractError, OSError, UnicodeError, ValueError) as exc:
                    add_error(
                        contract_findings,
                        "readiness-evidence-decision-closure",
                        item_location,
                        str(exc),
                    )
        elif not valid_external_reference(reference):
            add_error(
                contract_findings,
                "readiness-evidence-external",
                f"{item_location}.ref",
                "Expected a persistent identifier: canonical https://doi.org URI or URN.",
            )

        signatures.append(
            json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False)
        )
        validated.append(item)

    if len(signatures) != len(set(signatures)):
        add_error(
            contract_findings,
            "readiness-evidence-duplicate",
            location,
            "Duplicate evidence references are not allowed.",
        )
    return validated


def validate_policy_document(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    allowed = {
        "schema_version",
        "policy_id",
        "version",
        "assessor",
        "domain",
        "applicable_study_types",
        "applicable_data_requirements",
        "methodological_basis",
        "authorizations",
        "gates",
    }
    validate_keys(document, allowed, allowed, "gate_policy.", findings)
    if document.get("schema_version") != POLICY_SCHEMA:
        add_error(
            findings,
            "policy-schema",
            "gate_policy.schema_version",
            f"Expected {POLICY_SCHEMA}.",
        )
    require_string(document, "policy_id", findings, "gate_policy.")
    require_string(document, "version", findings, "gate_policy.")
    require_string(document, "domain", findings, "gate_policy.")
    validate_string_list(
        document.get("applicable_study_types"),
        "gate_policy.applicable_study_types",
        findings,
        allow_empty=False,
    )
    data_requirements = validate_string_list(
        document.get("applicable_data_requirements"),
        "gate_policy.applicable_data_requirements",
        findings,
        allow_empty=False,
        allowed_literals={"none"},
    )
    invalid_data_requirements = sorted(set(data_requirements) - DATA_REQUIREMENT)
    if invalid_data_requirements:
        add_error(
            findings,
            "policy-data-requirement",
            "gate_policy.applicable_data_requirements",
            f"Invalid data requirements: {invalid_data_requirements}",
        )
    validate_string_list(
        document.get("methodological_basis"),
        "gate_policy.methodological_basis",
        findings,
        allow_empty=False,
    )

    assessor = document.get("assessor")
    if not isinstance(assessor, dict):
        add_error(
            findings,
            "policy-assessor",
            "gate_policy.assessor",
            "Expected an object.",
        )
    else:
        validate_keys(
            assessor,
            {"name", "version"},
            {"name", "version"},
            "gate_policy.assessor.",
            findings,
        )
        require_string(assessor, "name", findings, "gate_policy.assessor.")
        require_string(assessor, "version", findings, "gate_policy.assessor.")

    authorizations = document.get("authorizations")
    if not isinstance(authorizations, list) or not authorizations:
        add_error(
            findings,
            "policy-authorizations",
            "gate_policy.authorizations",
            "Expected at least one authorization.",
        )
        authorizations = []
    seen_authorizations: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
    for index, authorization in enumerate(authorizations):
        location = f"gate_policy.authorizations[{index}]"
        if not isinstance(authorization, dict):
            add_error(findings, "policy-authorization", location, "Expected an object.")
            continue
        keys = {"analysis_mode", "claim_classes", "validation_levels"}
        validate_keys(authorization, keys, keys, f"{location}.", findings)
        if not is_string_enum(authorization.get("analysis_mode"), ANALYSIS_MODE):
            add_error(
                findings,
                "policy-analysis-mode",
                f"{location}.analysis_mode",
                "Invalid analysis mode.",
            )
        claims = validate_string_list(
            authorization.get("claim_classes"),
            f"{location}.claim_classes",
            findings,
            allow_empty=False,
        )
        levels = validate_string_list(
            authorization.get("validation_levels"),
            f"{location}.validation_levels",
            findings,
            allow_empty=False,
            allowed_literals={"none"},
        )
        for claim in claims:
            if claim not in CLAIM_CLASS:
                add_error(
                    findings,
                    "policy-claim-class",
                    f"{location}.claim_classes",
                    f"Invalid claim class: {claim}",
                )
        for level in levels:
            if level not in VALIDATION_LEVEL:
                add_error(
                    findings,
                    "policy-validation-level",
                    f"{location}.validation_levels",
                    f"Invalid validation level: {level}",
                )
        signature = (
            str(authorization.get("analysis_mode")),
            tuple(sorted(claims)),
            tuple(sorted(levels)),
        )
        if signature in seen_authorizations:
            add_error(
                findings,
                "policy-authorization-duplicate",
                location,
                "Duplicate authorization.",
            )
        seen_authorizations.add(signature)

    policy_gates = document.get("gates")
    if not isinstance(policy_gates, list) or not policy_gates:
        add_error(
            findings,
            "policy-gates",
            "gate_policy.gates",
            "Expected at least one policy gate.",
        )
        policy_gates = []
    gate_map: dict[str, dict[str, Any]] = {}
    for index, gate in enumerate(policy_gates):
        location = f"gate_policy.gates[{index}]"
        if not isinstance(gate, dict):
            add_error(findings, "policy-gate", location, "Expected an object.")
            continue
        keys = {
            "gate_id",
            "required_for_ready",
            "allow_na",
            "requirement",
            "applicability",
            "evaluation_method",
            "pass_condition",
            "required_evidence_kinds",
            "failure_effect",
        }
        validate_keys(gate, keys, keys, f"{location}.", findings)
        require_string(gate, "gate_id", findings, f"{location}.")
        require_string(gate, "requirement", findings, f"{location}.")
        require_string(gate, "applicability", findings, f"{location}.")
        require_string(gate, "evaluation_method", findings, f"{location}.")
        require_string(gate, "pass_condition", findings, f"{location}.")
        evidence_kinds = validate_string_list(
            gate.get("required_evidence_kinds"),
            f"{location}.required_evidence_kinds",
            findings,
            allow_empty=False,
        )
        invalid_evidence_kinds = sorted(set(evidence_kinds) - EVIDENCE_KINDS)
        if invalid_evidence_kinds:
            add_error(
                findings,
                "policy-gate-evidence-kind",
                f"{location}.required_evidence_kinds",
                f"Invalid evidence kinds: {invalid_evidence_kinds}",
            )
        if type(gate.get("required_for_ready")) is not bool:
            add_error(
                findings,
                "policy-gate-required",
                f"{location}.required_for_ready",
                "Expected a boolean.",
            )
        if type(gate.get("allow_na")) is not bool:
            add_error(
                findings,
                "policy-gate-allow-na",
                f"{location}.allow_na",
                "Expected a boolean.",
            )
        if not is_string_enum(gate.get("failure_effect"), {"block", "review"}):
            add_error(
                findings,
                "policy-gate-failure-effect",
                f"{location}.failure_effect",
                "Expected block or review.",
            )
        elif (
            gate.get("required_for_ready") is True
            and gate.get("failure_effect") != "block"
        ) or (
            gate.get("required_for_ready") is False
            and gate.get("failure_effect") != "review"
        ):
            add_error(
                findings,
                "policy-gate-failure-effect",
                f"{location}.failure_effect",
                "failure_effect must be block for required gates and review for advisory gates.",
            )
        gate_id = gate.get("gate_id")
        if isinstance(gate_id, str) and gate_id:
            if gate_id in gate_map:
                add_error(
                    findings,
                    "policy-gate-duplicate",
                    location,
                    f"Duplicate gate_id: {gate_id}",
                )
            else:
                gate_map[gate_id] = gate
    return {"gate_map": gate_map, "document": document}, findings


def validate_analysis_spec_document(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    keys = {
        "schema_version",
        "analysis_id",
        "scope_id",
        "question",
        "intended_use",
        "study_type",
        "data_requirement",
        "analysis_mode",
        "requested_claim_class",
        "target_validation_level",
        "input_source_ids",
        "independent_unit",
        "observation_unit",
        "estimand",
        "prespecification",
        "design",
        "domain",
        "domain_spec",
        "backend_revision",
        "entry_points",
        "domain_parameters",
        "created_at",
    }
    validate_keys(document, keys, keys, "analysis_spec.", findings)
    if document.get("schema_version") != ANALYSIS_SPEC_SCHEMA:
        add_error(
            findings,
            "analysis-spec-schema",
            "analysis_spec.schema_version",
            f"Expected {ANALYSIS_SPEC_SCHEMA}.",
        )
    for key in (
        "analysis_id",
        "scope_id",
        "question",
        "intended_use",
        "study_type",
        "independent_unit",
        "observation_unit",
        "estimand",
        "domain",
    ):
        require_string(document, key, findings, "analysis_spec.")
    if not is_string_enum(document.get("data_requirement"), DATA_REQUIREMENT):
        add_error(
            findings,
            "analysis-spec-data-requirement",
            "analysis_spec.data_requirement",
            "Expected none or data_bearing.",
        )
    if not is_string_enum(document.get("analysis_mode"), ANALYSIS_MODE):
        add_error(
            findings,
            "analysis-spec-mode",
            "analysis_spec.analysis_mode",
            "Invalid analysis mode.",
        )
    if not is_string_enum(document.get("requested_claim_class"), CLAIM_CLASS):
        add_error(
            findings,
            "analysis-spec-claim-class",
            "analysis_spec.requested_claim_class",
            "Invalid claim class.",
        )
    if not is_string_enum(document.get("target_validation_level"), VALIDATION_LEVEL):
        add_error(
            findings,
            "analysis-spec-validation-level",
            "analysis_spec.target_validation_level",
            "Invalid validation level.",
        )
    input_source_ids = validate_string_list(
        document.get("input_source_ids"),
        "analysis_spec.input_source_ids",
        findings,
        allow_empty=True,
    )
    data_requirement = document.get("data_requirement")
    if data_requirement == "data_bearing" and not input_source_ids:
        add_error(
            findings,
            "analysis-spec-source-required",
            "analysis_spec.input_source_ids",
            "A data-bearing analysis requires at least one source ID.",
        )
    elif data_requirement == "none" and input_source_ids:
        add_error(
            findings,
            "analysis-spec-source-not-applicable",
            "analysis_spec.input_source_ids",
            "A data-free analysis cannot declare input source IDs.",
        )
    if not is_string_enum(
        document.get("prespecification"),
        {
            "preregistered",
            "prespecified_not_preregistered",
            "post_hoc",
            "not_applicable",
        },
    ):
        add_error(
            findings,
            "analysis-spec-prespecification",
            "analysis_spec.prespecification",
            "Invalid prespecification state.",
        )
    design = document.get("design")
    if not isinstance(design, dict):
        add_error(
            findings,
            "analysis-spec-design",
            "analysis_spec.design",
            "Expected a structured design declaration.",
        )
    else:
        validate_keys(
            design,
            DESIGN_KEYS,
            DESIGN_KEYS,
            "analysis_spec.design.",
            findings,
        )
        for key in DESIGN_KEYS - {"unit_hierarchy", "protocol_deviation_status"}:
            require_string(design, key, findings, "analysis_spec.design.")
        unit_hierarchy = validate_string_list(
            design.get("unit_hierarchy"),
            "analysis_spec.design.unit_hierarchy",
            findings,
            allow_empty=False,
        )
        independent_unit = document.get("independent_unit")
        observation_unit = document.get("observation_unit")
        for field, unit in (
            ("independent_unit", independent_unit),
            ("observation_unit", observation_unit),
        ):
            if is_concrete_string(unit) and unit not in unit_hierarchy:
                add_error(
                    findings,
                    "analysis-spec-unit-hierarchy-closure",
                    f"analysis_spec.{field}",
                    f"{field} must occur in design.unit_hierarchy.",
                )
        if (
            is_concrete_string(independent_unit)
            and is_concrete_string(observation_unit)
            and unit_hierarchy
            and (
                unit_hierarchy[0] != independent_unit
                or unit_hierarchy[-1] != observation_unit
            )
        ):
            add_error(
                findings,
                "analysis-spec-unit-hierarchy-order",
                "analysis_spec.design.unit_hierarchy",
                "unit_hierarchy must start at independent_unit and end at observation_unit.",
            )
        if not is_string_enum(
            design.get("protocol_deviation_status"),
            {"none", "documented", "unresolved"},
        ):
            add_error(
                findings,
                "analysis-spec-protocol-deviation",
                "analysis_spec.design.protocol_deviation_status",
                "Expected none, documented or unresolved.",
            )
    domain_spec = document.get("domain_spec")
    if domain_spec is not None:
        if not isinstance(domain_spec, dict):
            add_error(
                findings,
                "analysis-spec-domain-spec",
                "analysis_spec.domain_spec",
                "Expected a path/SHA-256 binding or null.",
            )
        else:
            validate_keys(
                domain_spec,
                BINDING_KEYS,
                BINDING_KEYS,
                "analysis_spec.domain_spec.",
                findings,
            )
            if not isinstance(domain_spec.get("path"), str) or not domain_spec.get(
                "path"
            ):
                add_error(
                    findings,
                    "analysis-spec-domain-spec-path",
                    "analysis_spec.domain_spec.path",
                    "Expected a non-empty project-relative path.",
                )
            if not valid_sha256(domain_spec.get("sha256")):
                add_error(
                    findings,
                    "analysis-spec-domain-spec-sha256",
                    "analysis_spec.domain_spec.sha256",
                    "Expected a lowercase SHA-256.",
                )
    if data_requirement == "data_bearing" and domain_spec is None:
        add_error(
            findings,
            "analysis-spec-domain-spec-required",
            "analysis_spec.domain_spec",
            "A data-bearing analysis requires a domain-specific spec binding.",
        )
    elif data_requirement == "none" and domain_spec is not None:
        add_error(
            findings,
            "analysis-spec-domain-spec-not-applicable",
            "analysis_spec.domain_spec",
            "A data-free analysis must use a null domain_spec.",
        )
    backend_revision = document.get("backend_revision")
    if backend_revision is not None and not is_concrete_string(backend_revision):
        add_error(
            findings,
            "analysis-spec-backend-revision",
            "analysis_spec.backend_revision",
            "Expected a concrete, non-placeholder string or null.",
        )
    entry_points = validate_string_list(
        document.get("entry_points"),
        "analysis_spec.entry_points",
        findings,
        allow_empty=False,
    )
    for index, entry_point in enumerate(entry_points):
        try:
            portable_project_relative(entry_point)
        except ContractError as exc:
            add_error(
                findings,
                "analysis-spec-entry-point",
                f"analysis_spec.entry_points[{index}]",
                str(exc),
            )
    if not isinstance(document.get("domain_parameters"), dict):
        add_error(
            findings,
            "analysis-spec-domain-parameters",
            "analysis_spec.domain_parameters",
            "Expected an object.",
        )
    elif data_requirement == "data_bearing" and not document["domain_parameters"]:
        add_error(
            findings,
            "analysis-spec-domain-parameters-required",
            "analysis_spec.domain_parameters",
            "A data-bearing analysis requires non-empty domain parameters.",
        )
    try:
        parse_rfc3339(document.get("created_at"))
    except ContractError as exc:
        add_error(
            findings,
            "analysis-spec-created-at",
            "analysis_spec.created_at",
            str(exc),
        )
    return {
        "input_source_ids": input_source_ids,
        "entry_points": entry_points,
        "document": document,
    }, findings


def validate_document(
    root: Path,
    document: dict[str, Any],
    max_age_days: int | None,
    *,
    now: datetime | None = None,
    current_code_revision: str | None = None,
    current_code_dirty: bool | None = None,
    current_backend_revision: str | None = None,
) -> dict[str, Any]:
    contract_findings: list[dict[str, str]] = []
    currency_findings: list[dict[str, str]] = []
    design_blocker = False
    validate_keys(
        document,
        READINESS_KEYS,
        REQUIRED_READINESS_KEYS,
        "",
        contract_findings,
    )
    if document.get("schema_version") != READINESS_SCHEMA:
        add_error(
            contract_findings,
            "readiness-schema",
            "schema_version",
            f"Expected {READINESS_SCHEMA}.",
        )
    for key in (
        "readiness_id",
        "analysis_id",
        "scope_id",
        "intended_use",
        "code_revision",
    ):
        require_string(document, key, contract_findings)
    validate_readiness_id_uniqueness(
        root, document.get("readiness_id"), contract_findings
    )
    require_enum(
        document,
        "source_provenance_status",
        SOURCE_PROVENANCE_STATUS,
        contract_findings,
    )
    require_enum(document, "readiness_status", READINESS, contract_findings)
    require_enum(document, "analysis_mode", ANALYSIS_MODE, contract_findings)
    require_enum(document, "requested_claim_class", CLAIM_CLASS, contract_findings)
    require_enum(
        document,
        "achieved_validation_level",
        VALIDATION_LEVEL,
        contract_findings,
    )
    require_enum(
        document,
        "claim_authorization",
        CLAIM_AUTHORIZATION,
        contract_findings,
    )
    require_enum(document, "lifecycle_status", LIFECYCLE, contract_findings)

    assessor = document.get("assessor")
    if not isinstance(assessor, dict):
        add_error(
            contract_findings,
            "readiness-assessor",
            "assessor",
            "Expected an object.",
        )
    else:
        validate_keys(
            assessor,
            {"name", "version"},
            {"name", "version"},
            "assessor.",
            contract_findings,
        )
        require_string(assessor, "name", contract_findings, "assessor.")
        require_string(assessor, "version", contract_findings, "assessor.")

    assessed_at: datetime | None = None
    check_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        assessed_at = parse_rfc3339(document.get("assessed_at"))
    except ContractError as exc:
        add_error(
            contract_findings,
            "readiness-assessed-at",
            "assessed_at",
            str(exc),
        )
    if assessed_at and assessed_at > check_time + timedelta(minutes=5):
        add_error(
            contract_findings,
            "readiness-future",
            "assessed_at",
            "Assessment time is in the future.",
        )
    if (
        assessed_at
        and max_age_days is not None
        and check_time - assessed_at > timedelta(days=max_age_days)
    ):
        age_days = (check_time - assessed_at).total_seconds() / 86400
        add_error(
            currency_findings,
            "readiness-expired",
            "assessed_at",
            f"Readiness assessment is {age_days:.1f} days old; maximum is {max_age_days}.",
        )

    source_provenance_status = document.get("source_provenance_status")
    input_source_ids = validate_string_list(
        document.get("input_source_ids"),
        "input_source_ids",
        contract_findings,
        allow_empty=source_provenance_status == "not_applicable",
    )
    if source_provenance_status == "not_applicable":
        if document.get("input_manifest") is not None:
            add_error(
                contract_findings,
                "readiness-source-not-applicable",
                "input_manifest",
                "not_applicable source status requires a null input_manifest.",
            )
        if input_source_ids:
            add_error(
                contract_findings,
                "readiness-source-not-applicable",
                "input_source_ids",
                "not_applicable source status requires no input source IDs.",
            )
    elif document.get("input_manifest") is None:
        add_error(
            contract_findings,
            "readiness-input-manifest",
            "input_manifest",
            "A source manifest binding is required unless sources are not applicable.",
        )

    readiness_status = document.get("readiness_status")
    authorized_claim_classes = validate_string_list(
        document.get("authorized_claim_classes"),
        "authorized_claim_classes",
        contract_findings,
        allow_empty=readiness_status != "ready",
    )
    prohibited_claim_classes = validate_string_list(
        document.get("prohibited_claim_classes"),
        "prohibited_claim_classes",
        contract_findings,
        allow_empty=True,
    )
    validate_string_list(
        document.get("claim_boundary_notes"),
        "claim_boundary_notes",
        contract_findings,
        allow_empty=True,
    )
    for location, classes in (
        ("authorized_claim_classes", authorized_claim_classes),
        ("prohibited_claim_classes", prohibited_claim_classes),
    ):
        invalid_classes = sorted(set(classes) - CLAIM_CLASS)
        if invalid_classes:
            add_error(
                contract_findings,
                "readiness-claim-class-list",
                location,
                f"Invalid claim classes: {invalid_classes}",
            )
    requested_claim_class = document.get("requested_claim_class")
    claim_authorization = document.get("claim_authorization")
    if readiness_status == "ready":
        if requested_claim_class not in authorized_claim_classes:
            add_error(
                contract_findings,
                "readiness-claim-class-not-authorized",
                "requested_claim_class",
                "A ready report must authorize its requested claim class.",
            )
        if claim_authorization != "authorized":
            add_error(
                contract_findings,
                "readiness-claim-authorization",
                "claim_authorization",
                "A ready report requires claim_authorization=authorized.",
            )
    elif readiness_status == "review":
        if authorized_claim_classes:
            add_error(
                contract_findings,
                "readiness-claim-authorization",
                "authorized_claim_classes",
                "A review report cannot list fully authorized claim classes.",
            )
        if claim_authorization != "conditional":
            add_error(
                contract_findings,
                "readiness-claim-authorization",
                "claim_authorization",
                "A review report requires claim_authorization=conditional.",
            )
    elif readiness_status == "blocked":
        if authorized_claim_classes:
            add_error(
                contract_findings,
                "readiness-claim-authorization",
                "authorized_claim_classes",
                "A blocked report cannot authorize claim classes.",
            )
        if claim_authorization != "not_authorized":
            add_error(
                contract_findings,
                "readiness-claim-authorization",
                "claim_authorization",
                "A blocked report requires claim_authorization=not_authorized.",
            )
    overlap = sorted(set(authorized_claim_classes) & set(prohibited_claim_classes))
    if overlap:
        add_error(
            contract_findings,
            "readiness-claim-overlap",
            "authorized_claim_classes",
            f"Claim classes cannot be both allowed and prohibited: {overlap}",
        )

    if type(document.get("code_dirty")) is not bool:
        add_error(
            contract_findings,
            "readiness-code-dirty",
            "code_dirty",
            "Expected a boolean.",
        )
    backend_revision = document.get("backend_revision")
    if backend_revision is not None and not is_concrete_string(backend_revision):
        add_error(
            contract_findings,
            "readiness-backend-revision",
            "backend_revision",
            "Expected a concrete, non-placeholder string or null.",
        )

    binding_status: dict[str, str] = {}
    binding_paths: dict[str, Path | None] = {}
    for label in (
        "gate_policy",
        "analysis_spec",
        "code_manifest",
        "environment_snapshot",
    ):
        status, path = validate_binding(
            root,
            document.get(label),
            label,
            contract_findings,
            currency_findings,
        )
        binding_status[label] = status
        binding_paths[label] = path
    if source_provenance_status != "not_applicable":
        status, path = validate_binding(
            root,
            document.get("input_manifest"),
            "input_manifest",
            contract_findings,
            currency_findings,
        )
        binding_status["input_manifest"] = status
        binding_paths["input_manifest"] = path
    environment_path = binding_paths.get("environment_snapshot")
    if binding_status.get("environment_snapshot") == "current" and environment_path:
        try:
            environment_bytes = environment_path.read_bytes()
            if not environment_bytes.strip():
                add_error(
                    contract_findings,
                    "readiness-environment-empty",
                    "environment_snapshot",
                    "Environment snapshot must contain non-whitespace content.",
                )
            else:
                try:
                    environment_text = environment_bytes.decode("utf-8").strip()
                except UnicodeDecodeError:
                    environment_text = ""
                if environment_text and PLACEHOLDER_RE.fullmatch(environment_text):
                    add_error(
                        contract_findings,
                        "readiness-environment-placeholder",
                        "environment_snapshot",
                        "Environment snapshot cannot be only a placeholder.",
                    )
        except OSError as exc:
            add_error(
                currency_findings,
                "readiness-environment-unverifiable",
                "environment_snapshot",
                str(exc),
            )

    dependencies = document.get("dependencies", [])
    dependency_statuses: list[str] = []
    if not isinstance(dependencies, list):
        add_error(
            contract_findings,
            "readiness-dependencies",
            "dependencies",
            "Expected a list of file bindings.",
        )
    else:
        for index, dependency in enumerate(dependencies):
            status, _ = validate_binding(
                root,
                dependency,
                f"dependencies[{index}]",
                contract_findings,
                currency_findings,
            )
            dependency_statuses.append(status)

    revision_statuses: list[str] = []
    if current_code_revision is None:
        currency_findings.append(
            finding(
                "warning",
                "readiness-code-revision-unchecked",
                "code_revision",
                "Current code revision was not supplied; revision currency is unknown.",
            )
        )
        revision_statuses.append("unknown")
    elif document.get("code_revision") != current_code_revision:
        add_error(
            currency_findings,
            "readiness-code-revision-stale",
            "code_revision",
            "Recorded code revision differs from the supplied current revision.",
        )
        revision_statuses.append("stale")
    if current_code_dirty is None:
        currency_findings.append(
            finding(
                "warning",
                "readiness-code-dirty-unchecked",
                "code_dirty",
                "Current code dirty state was not supplied; code-state currency is unknown.",
            )
        )
        revision_statuses.append("unknown")
    elif document.get("code_dirty") != current_code_dirty:
        add_error(
            currency_findings,
            "readiness-code-dirty-stale",
            "code_dirty",
            "Recorded code dirty state differs from the supplied current state.",
        )
        revision_statuses.append("stale")
    if backend_revision is not None and current_backend_revision is None:
        currency_findings.append(
            finding(
                "warning",
                "readiness-backend-revision-unchecked",
                "backend_revision",
                "Current backend revision was not supplied; backend currency is unknown.",
            )
        )
        revision_statuses.append("unknown")
    elif (
        current_backend_revision is not None
        and backend_revision != current_backend_revision
    ):
        add_error(
            currency_findings,
            "readiness-backend-revision-stale",
            "backend_revision",
            "Recorded backend revision differs from the supplied current revision.",
        )
        revision_statuses.append("stale")

    policy: dict[str, Any] | None = None
    policy_contract_valid = False
    policy_path = binding_paths.get("gate_policy")
    if binding_status.get("gate_policy") == "current" and policy_path:
        try:
            policy_document = load_json_object(policy_path)
            policy, policy_findings = validate_policy_document(policy_document)
            contract_findings.extend(policy_findings)
            policy_contract_valid = not any(
                item["level"] == "error" for item in policy_findings
            )
        except ContractError as exc:
            add_error(
                contract_findings,
                "policy-read",
                "gate_policy",
                str(exc),
            )

    analysis_spec: dict[str, Any] | None = None
    analysis_spec_path = binding_paths.get("analysis_spec")
    if binding_status.get("analysis_spec") == "current" and analysis_spec_path:
        try:
            analysis_spec_document = load_json_object(analysis_spec_path)
            analysis_spec, spec_findings = validate_analysis_spec_document(
                analysis_spec_document
            )
            contract_findings.extend(spec_findings)
        except ContractError as exc:
            add_error(
                contract_findings,
                "analysis-spec-read",
                "analysis_spec",
                str(exc),
            )
    if analysis_spec:
        spec_document = analysis_spec["document"]
        data_requirement = spec_document.get("data_requirement")
        if (
            data_requirement == "data_bearing"
            and source_provenance_status == "not_applicable"
        ):
            add_error(
                contract_findings,
                "analysis-spec-source-status-mismatch",
                "source_provenance_status",
                "A data-bearing analysis cannot declare sources not applicable.",
            )
        elif (
            data_requirement == "none"
            and source_provenance_status != "not_applicable"
        ):
            add_error(
                contract_findings,
                "analysis-spec-source-status-mismatch",
                "source_provenance_status",
                "A data-free analysis must declare sources not applicable.",
            )
        try:
            spec_created_at = parse_rfc3339(spec_document.get("created_at"))
        except ContractError:
            spec_created_at = None
        if (
            spec_created_at
            and assessed_at
            and spec_created_at > assessed_at + timedelta(minutes=5)
        ):
            add_error(
                contract_findings,
                "analysis-spec-after-assessment",
                "analysis_spec.created_at",
                "Analysis specification was created after the readiness assessment.",
            )
        same_fields = {
            "analysis_id": "analysis_id",
            "scope_id": "scope_id",
            "intended_use": "intended_use",
            "analysis_mode": "analysis_mode",
            "requested_claim_class": "requested_claim_class",
            "backend_revision": "backend_revision",
        }
        for report_key, spec_key in same_fields.items():
            if document.get(report_key) != spec_document.get(spec_key):
                add_error(
                    contract_findings,
                    "analysis-spec-mismatch",
                    report_key,
                    f"Readiness {report_key} does not match the bound analysis spec.",
                )
        if set(input_source_ids) != set(analysis_spec["input_source_ids"]):
            add_error(
                contract_findings,
                "analysis-spec-source-ids",
                "input_source_ids",
                "Readiness source IDs do not match the bound analysis spec.",
            )
        domain_spec = spec_document.get("domain_spec")
        if (
            readiness_status == "ready"
            and source_provenance_status != "not_applicable"
            and domain_spec is None
        ):
            add_error(
                contract_findings,
                "analysis-spec-domain-spec-required",
                "analysis_spec.domain_spec",
                "A data-bearing ready declaration requires a bound domain-specific spec.",
            )
        if (
            readiness_status == "ready"
            and source_provenance_status != "not_applicable"
            and not spec_document.get("domain_parameters")
        ):
            add_error(
                contract_findings,
                "analysis-spec-domain-parameters-required",
                "analysis_spec.domain_parameters",
                "A data-bearing ready declaration requires non-empty domain parameters.",
            )
        if domain_spec is not None:
            status, _ = validate_binding(
                root,
                domain_spec,
                "analysis_spec.domain_spec",
                contract_findings,
                currency_findings,
            )
            dependency_statuses.append(status)

        mode = document.get("analysis_mode")
        claim = document.get("requested_claim_class")
        achieved_validation = document.get("achieved_validation_level")
        prespecification = spec_document.get("prespecification")
        incompatible_reason: str | None = None
        if mode == "descriptive" and claim != "observation":
            incompatible_reason = (
                "Descriptive mode can authorize observation claims only."
            )
        elif claim == "prediction" and mode != "predictive":
            incompatible_reason = "Prediction claims require predictive analysis mode."
        elif is_string_enum(claim, {"causal_effect", "mechanism"}) and mode != "causal":
            incompatible_reason = (
                "Causal-effect or mechanism claims require causal analysis mode."
            )
        elif claim == "clinical_utility" and (
            not is_string_enum(mode, {"predictive", "causal"})
            or achieved_validation != "prospective"
        ):
            incompatible_reason = "Clinical-utility claims require predictive/causal mode and prospective validation."
        elif mode == "confirmatory" and prespecification not in {
            "preregistered",
            "prespecified_not_preregistered",
        }:
            design_blocker = True
            contract_findings.append(
                finding(
                    "warning",
                    "analysis-spec-confirmatory-prespecification",
                    "analysis_spec.prespecification",
                    "Confirmatory mode requires preregistered or prespecified analysis; readiness is blocked.",
                )
            )
        if (
            isinstance(spec_document.get("design"), dict)
            and spec_document["design"].get("protocol_deviation_status") == "unresolved"
        ):
            design_blocker = True
            contract_findings.append(
                finding(
                    "warning",
                    "analysis-spec-unresolved-deviation",
                    "analysis_spec.design.protocol_deviation_status",
                    "Unresolved protocol deviations block readiness.",
                )
            )
        if incompatible_reason:
            add_error(
                contract_findings,
                "analysis-spec-mode-claim-incompatible",
                "analysis_mode",
                incompatible_reason,
            )

    code_manifest_contract_status = "not_assessed"
    code_integrity_status = "not_assessed"
    code_manifest_path = binding_paths.get("code_manifest")
    if binding_status.get("code_manifest") == "current" and code_manifest_path:
        try:
            code_manifest = load_json_object(code_manifest_path)
            code_report = verify_source_manifest_document(root, code_manifest)
            code_manifest_contract_status = code_report["manifest_contract_status"]
            code_integrity_status = code_report["source_integrity_status"]
            if code_manifest_contract_status == "invalid":
                contract_findings.extend(code_report["findings"])
            else:
                currency_findings.extend(code_report["findings"])
                try:
                    code_manifest_generated_at = parse_rfc3339(
                        code_manifest.get("generated_at")
                    )
                except ContractError:
                    code_manifest_generated_at = None
                if (
                    code_manifest_generated_at
                    and assessed_at
                    and code_manifest_generated_at > assessed_at + timedelta(minutes=5)
                ):
                    add_error(
                        contract_findings,
                        "code-manifest-after-assessment",
                        "code_manifest.generated_at",
                        "Code manifest was generated after the readiness assessment.",
                    )
                if analysis_spec:
                    recorded_code_paths = {
                        entry.get("path")
                        for entry in code_manifest.get("entries", [])
                        if isinstance(entry, dict)
                        and entry.get("hash_status") == "recorded"
                    }
                    missing_entry_points = sorted(
                        set(analysis_spec.get("entry_points", []))
                        - recorded_code_paths
                    )
                    if missing_entry_points:
                        add_error(
                            contract_findings,
                            "code-manifest-entry-points-missing",
                            "code_manifest.entries",
                            "Code manifest does not cover analysis entry points: "
                            f"{missing_entry_points}",
                        )
                if code_integrity_status == "fail":
                    dependency_statuses.append("stale")
                elif code_integrity_status == "review":
                    dependency_statuses.append("unknown")
        except ContractError as exc:
            add_error(
                contract_findings,
                "readiness-code-manifest",
                "code_manifest",
                str(exc),
            )

    source_integrity_status = "not_assessed"
    manifest_contract_status = "not_assessed"
    manifest_document: dict[str, Any] | None = None
    manifest_path = binding_paths.get("input_manifest")
    if (
        source_provenance_status != "not_applicable"
        and binding_status.get("input_manifest") == "current"
        and manifest_path
    ):
        try:
            manifest_document = load_json_object(manifest_path)
            source_report = verify_source_manifest_document(root, manifest_document)
            manifest_contract_status = source_report["manifest_contract_status"]
            source_integrity_status = source_report["source_integrity_status"]
            if manifest_contract_status == "invalid":
                contract_findings.extend(source_report["findings"])
            else:
                currency_findings.extend(source_report["findings"])
                try:
                    manifest_generated_at = parse_rfc3339(
                        manifest_document.get("generated_at")
                    )
                except ContractError:
                    manifest_generated_at = None
                if (
                    manifest_generated_at
                    and assessed_at
                    and manifest_generated_at > assessed_at + timedelta(minutes=5)
                ):
                    add_error(
                        contract_findings,
                        "source-manifest-after-assessment",
                        "input_manifest.generated_at",
                        "Source manifest was generated after the readiness assessment.",
                    )
                manifest_ids = {
                    entry.get("source_id")
                    for entry in manifest_document.get("entries", [])
                    if isinstance(entry, dict)
                }
                missing_ids = sorted(set(input_source_ids) - manifest_ids)
                if missing_ids:
                    add_error(
                        contract_findings,
                        "readiness-source-id",
                        "input_source_ids",
                        f"Source IDs are absent from the bound manifest: {missing_ids}",
                    )
                if source_provenance_status == "verified":
                    provenance_gaps = source_provenance_gaps(manifest_document)
                    if provenance_gaps:
                        add_error(
                            contract_findings,
                            "readiness-source-provenance-incomplete",
                            "input_manifest.source_context",
                            "source_provenance_status=verified requires concrete "
                            f"identity metadata; missing/unknown: {provenance_gaps}",
                        )
        except ContractError as exc:
            add_error(
                contract_findings,
                "readiness-input-manifest",
                "input_manifest",
                str(exc),
            )

    gates_value = document.get("gates")
    if not isinstance(gates_value, list) or not gates_value:
        add_error(
            contract_findings,
            "readiness-gates",
            "gates",
            "Expected at least one gate.",
        )
        gates_value = []
    report_gates: dict[str, dict[str, Any]] = {}
    mandatory_problem = design_blocker or is_string_enum(
        source_provenance_status, {"unverified", "conflicting"}
    )
    advisory_problem = False
    for index, gate in enumerate(gates_value):
        location = f"gates[{index}]"
        if not isinstance(gate, dict):
            add_error(
                contract_findings,
                "readiness-gate",
                location,
                "Expected an object.",
            )
            continue
        validate_keys(gate, GATE_KEYS, GATE_KEYS, f"{location}.", contract_findings)
        gate_id = gate.get("gate_id")
        require_string(gate, "gate_id", contract_findings, f"{location}.")
        require_string(gate, "requirement", contract_findings, f"{location}.")
        if type(gate.get("required_for_ready")) is not bool:
            add_error(
                contract_findings,
                "readiness-gate-required",
                f"{location}.required_for_ready",
                "Expected a boolean.",
            )
        status = gate.get("status")
        if not is_string_enum(status, GATE_STATUS):
            add_error(
                contract_findings,
                "readiness-gate-status",
                f"{location}.status",
                f"Expected one of {sorted(GATE_STATUS)}.",
            )
        evidence = validate_evidence_list(
            root,
            gate.get("evidence"),
            f"{location}.evidence",
            contract_findings,
            currency_findings,
            allow_empty=not is_string_enum(status, {"PASS", "NA"}),
            gate_status=status,
            analysis_id=document.get("analysis_id"),
            scope_id=document.get("scope_id"),
            assessed_at=assessed_at,
            analysis_spec_binding=document.get("analysis_spec"),
            environment_snapshot_binding=document.get("environment_snapshot"),
            code_revision=document.get("code_revision"),
            code_dirty=document.get("code_dirty"),
            backend_revision=document.get("backend_revision"),
            entry_points=(
                analysis_spec.get("entry_points", []) if analysis_spec else []
            ),
            data_requirement=(
                analysis_spec.get("document", {}).get("data_requirement")
                if analysis_spec
                else None
            ),
            input_source_ids=input_source_ids,
        )
        if is_string_enum(status, {"PASS", "NA"}) and not evidence:
            add_error(
                contract_findings,
                "readiness-gate-evidence",
                f"{location}.evidence",
                "PASS/NA requires at least one typed evidence reference.",
            )
        if not isinstance(gate.get("impact"), str):
            add_error(
                contract_findings,
                "readiness-gate-impact",
                f"{location}.impact",
                "Expected a string.",
            )
        if not isinstance(gate.get("remediation"), str):
            add_error(
                contract_findings,
                "readiness-gate-remediation",
                f"{location}.remediation",
                "Expected a string.",
            )
        elif is_string_enum(status, {"FAIL", "UNKNOWN"}) and not is_concrete_string(
            gate.get("remediation")
        ):
            add_error(
                contract_findings,
                "readiness-gate-remediation",
                f"{location}.remediation",
                "FAIL/UNKNOWN requires remediation.",
            )
        if isinstance(gate_id, str) and gate_id:
            if gate_id in report_gates:
                add_error(
                    contract_findings,
                    "readiness-gate-duplicate",
                    location,
                    f"Duplicate gate_id: {gate_id}",
                )
            else:
                report_gates[gate_id] = {**gate, "evidence": evidence}
        if is_string_enum(status, {"FAIL", "UNKNOWN"}):
            if gate.get("required_for_ready") is True:
                mandatory_problem = True
            elif gate.get("required_for_ready") is False:
                advisory_problem = True

    policy_status = (
        "nonconformant"
        if policy is not None and not policy_contract_valid
        else "not_assessed"
    )
    if policy and policy_contract_valid:
        policy_status = "conformant"
        policy_document = policy["document"]
        if analysis_spec:
            spec_document = analysis_spec["document"]
            if policy_document.get("domain") != spec_document.get("domain"):
                add_error(
                    contract_findings,
                    "policy-domain-mismatch",
                    "gate_policy.domain",
                    "Gate policy domain does not match the analysis specification.",
                )
                policy_status = "nonconformant"
            if spec_document.get("study_type") not in policy_document.get(
                "applicable_study_types", []
            ):
                add_error(
                    contract_findings,
                    "policy-study-type-not-applicable",
                    "analysis_spec.study_type",
                    "Analysis study_type is outside the gate policy applicability set.",
                )
                policy_status = "nonconformant"
            if spec_document.get("data_requirement") not in policy_document.get(
                "applicable_data_requirements", []
            ):
                add_error(
                    contract_findings,
                    "policy-data-requirement-not-applicable",
                    "analysis_spec.data_requirement",
                    "Analysis data requirement is outside the gate policy applicability set.",
                )
                policy_status = "nonconformant"
        policy_assessor = policy_document.get("assessor", {}).get("name")
        report_assessor = assessor.get("name") if isinstance(assessor, dict) else None
        if policy_assessor != report_assessor:
            add_error(
                contract_findings,
                "policy-assessor-mismatch",
                "assessor.name",
                "Report assessor does not match the gate policy.",
            )
            policy_status = "nonconformant"
        policy_assessor_version = policy_document.get("assessor", {}).get("version")
        report_assessor_version = (
            assessor.get("version") if isinstance(assessor, dict) else None
        )
        if policy_assessor_version != report_assessor_version:
            add_error(
                contract_findings,
                "policy-assessor-version-mismatch",
                "assessor.version",
                "Report assessor version does not match the gate policy.",
            )
            policy_status = "nonconformant"
        policy_gates = policy["gate_map"]
        missing = sorted(set(policy_gates) - set(report_gates))
        extra = sorted(set(report_gates) - set(policy_gates))
        if missing:
            add_error(
                contract_findings,
                "policy-gates-missing",
                "gates",
                f"Required policy gates are missing: {missing}",
            )
            policy_status = "nonconformant"
        if extra:
            add_error(
                contract_findings,
                "policy-gates-extra",
                "gates",
                f"Report contains gates absent from policy: {extra}",
            )
            policy_status = "nonconformant"
        for gate_id in sorted(set(policy_gates) & set(report_gates)):
            policy_gate = policy_gates[gate_id]
            report_gate = report_gates[gate_id]
            for key in ("required_for_ready", "requirement"):
                if report_gate.get(key) != policy_gate.get(key):
                    add_error(
                        contract_findings,
                        "policy-gate-mismatch",
                        f"gates.{gate_id}.{key}",
                        "Report gate differs from the bound policy.",
                    )
                    policy_status = "nonconformant"
            if (
                report_gate.get("status") == "NA"
                and policy_gate.get("allow_na") is not True
            ):
                add_error(
                    contract_findings,
                    "policy-gate-na-not-allowed",
                    f"gates.{gate_id}.status",
                    "The bound policy does not allow NA for this gate.",
                )
                policy_status = "nonconformant"
            if is_string_enum(report_gate.get("status"), {"PASS", "NA"}):
                actual_evidence_kinds = {
                    item.get("kind")
                    for item in report_gate.get("evidence", [])
                    if isinstance(item, dict) and isinstance(item.get("kind"), str)
                }
                missing_evidence_kinds = sorted(
                    set(policy_gate.get("required_evidence_kinds", []))
                    - actual_evidence_kinds
                )
                if missing_evidence_kinds:
                    add_error(
                        contract_findings,
                        "policy-gate-evidence-kinds",
                        f"gates.{gate_id}.evidence",
                        "PASS/NA evidence lacks policy-required kinds: "
                        f"{missing_evidence_kinds}",
                    )
                    policy_status = "nonconformant"
        authorized = any(
            authorization.get("analysis_mode") == document.get("analysis_mode")
            and document.get("requested_claim_class")
            in authorization.get("claim_classes", [])
            and document.get("achieved_validation_level")
            in authorization.get("validation_levels", [])
            for authorization in policy_document.get("authorizations", [])
            if isinstance(authorization, dict)
        )
        if readiness_status == "ready" and not authorized:
            add_error(
                contract_findings,
                "policy-authorization",
                "analysis_mode",
                "The mode/claim/validation tuple is not authorized by the bound gate policy.",
            )
            policy_status = "nonconformant"
        unauthorized_claim_classes = sorted(
            claim
            for claim in authorized_claim_classes
            if not any(
                authorization.get("analysis_mode") == document.get("analysis_mode")
                and claim in authorization.get("claim_classes", [])
                and document.get("achieved_validation_level")
                in authorization.get("validation_levels", [])
                for authorization in policy_document.get("authorizations", [])
                if isinstance(authorization, dict)
            )
        )
        if unauthorized_claim_classes:
            add_error(
                contract_findings,
                "policy-allowed-claim-classes",
                "authorized_claim_classes",
                "The bound policy does not authorize allowed claim classes "
                f"{unauthorized_claim_classes} for this mode and achieved validation level.",
            )
            policy_status = "nonconformant"

    computed_readiness: str | None = None
    if not any(item["level"] == "error" for item in contract_findings):
        computed_readiness = (
            "blocked"
            if mandatory_problem
            else "review"
            if advisory_problem
            else "ready"
        )
        if document.get("readiness_status") != computed_readiness:
            add_error(
                contract_findings,
                "readiness-status-inconsistent",
                "readiness_status",
                f"Declared {document.get('readiness_status')}, but gates and source status compute {computed_readiness}.",
            )

    all_binding_statuses = (
        list(binding_status.values()) + dependency_statuses + revision_statuses
    )
    if source_integrity_status == "fail":
        all_binding_statuses.append("stale")
    elif source_integrity_status == "review":
        all_binding_statuses.append("unknown")
    if "stale" in all_binding_statuses or any(
        item["level"] == "error" for item in currency_findings
    ):
        currency_status = "stale"
    elif "unknown" in all_binding_statuses or any(
        item["level"] == "warning" for item in currency_findings
    ):
        currency_status = "unknown"
    else:
        currency_status = "current"
    contract_status = (
        "invalid"
        if any(item["level"] == "error" for item in contract_findings)
        else "valid"
    )
    policy_declaration_current = (
        contract_status == "valid"
        and currency_status == "current"
        and policy_status == "conformant"
        and is_string_enum(source_provenance_status, {"verified", "not_applicable"})
        and document.get("readiness_status") == "ready"
        and document.get("lifecycle_status") == "current"
    )
    findings = contract_findings + currency_findings
    counts = {
        level: sum(item["level"] == level for item in findings)
        for level in ("error", "warning", "info")
    }
    return {
        "contract_status": contract_status,
        "currency_status": currency_status,
        "policy_status": policy_status,
        "code_manifest_contract_status": code_manifest_contract_status,
        "code_integrity_status": code_integrity_status,
        "manifest_contract_status": manifest_contract_status,
        "source_integrity_status": source_integrity_status,
        "source_provenance_status": source_provenance_status,
        "requested_claim_class": document.get("requested_claim_class"),
        "achieved_validation_level": document.get("achieved_validation_level"),
        "claim_authorization": document.get("claim_authorization"),
        "declared_claim_authorization": document.get("claim_authorization"),
        "declared_readiness": document.get("readiness_status"),
        "computed_readiness": computed_readiness,
        "policy_declaration_current": policy_declaration_current,
        "declared_ready_and_current": policy_declaration_current,
        "scientific_release_permitted": False,
        "scientific_validity": "not_determined_by_contract_validator",
        "counts": counts,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a legacy policy declaration and its freshness without "
            "determining scientific claim-release readiness."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("report")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Require a current policy declaration; never authorizes scientific release.",
    )
    parser.add_argument("--max-age-days", type=int)
    parser.add_argument("--current-code-revision")
    parser.add_argument("--current-code-dirty", choices=["true", "false"])
    parser.add_argument("--current-backend-revision")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.max_age_days is not None and args.max_age_days < 0:
        return cli_error("--max-age-days must be non-negative", json_mode=args.json)

    root = args.project.expanduser().resolve()
    if not root.is_dir():
        return cli_error(
            f"Project directory does not exist: {root}",
            json_mode=args.json,
            project=str(root),
            report=args.report,
        )
    try:
        report_path = resolve_project_relative(root, args.report, must_exist=True)
        document = load_json_object(report_path)
    except ContractError as exc:
        return cli_error(
            str(exc),
            json_mode=args.json,
            project=str(root),
            report=args.report,
        )

    result = {
        "project": str(root),
        "report": args.report,
        **validate_document(
            root,
            document,
            args.max_age_days,
            current_code_revision=args.current_code_revision,
            current_code_dirty=(
                args.current_code_dirty == "true"
                if args.current_code_dirty is not None
                else None
            ),
            current_backend_revision=args.current_backend_revision,
        ),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(
            "POLICY DECLARATION CONTRACT: "
            f"{result['contract_status'].upper()} | "
            f"CURRENCY: {result['currency_status'].upper()} | "
            f"POLICY: {result['policy_status'].upper()} | "
            f"DECLARED: {str(result['declared_readiness']).upper()}"
        )
        print("Scientific validity is not determined by this contract validator.")
        for item in result["findings"]:
            print(
                f"[{item['level'].upper()}] {item['code']} | "
                f"{item['path']} | {item['message']}"
            )

    if result["contract_status"] != "valid" or result["currency_status"] != "current":
        return 1
    if args.require_ready and not result["policy_declaration_current"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
