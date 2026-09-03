#!/usr/bin/env python3
"""Validate purpose-specific scientific readiness without claiming scientific truth."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from project_contracts import (
    ContractError,
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
from validate_readiness import (
    add_error,
    canonical_record_sha256,
    is_concrete_string,
    is_string_enum,
    parse_registry_ids,
    parse_source_ids,
    registry_row,
    source_provenance_gaps,
    validate_artifact_row,
    validate_binding,
    validate_evidence_list,
    validate_keys,
    validate_string_list,
)


READINESS_SCHEMA = "research-readiness/v2"
SPEC_SCHEMA = "research-analysis-spec/v2"
POLICY_SCHEMA = "readiness-gate-policy/v2"
ENVIRONMENT_SCHEMA = "research-environment/v1"
INVOCATION_SCHEMA = "research-invocation/v1"
PURPOSES = {
    "analysis_execution",
    "result_interpretation",
    "claim_communication",
    "decision_support",
}
NON_EXECUTION_PURPOSES = PURPOSES - {"analysis_execution"}
ANALYSIS_MODES = {"descriptive", "exploratory", "confirmatory", "predictive", "causal"}
CLAIM_CLASSES = {
    "observation",
    "association",
    "prediction",
    "causal_effect",
    "mechanism",
    "translational",
    "clinical_utility",
}
DATA_REQUIREMENTS = {"none", "data_bearing"}
READINESS_STATES = {"ready", "review", "blocked"}
LIFECYCLE_STATES = {"current", "superseded", "invalidated", "archived"}
SOURCE_STATES = {"verified", "unverified", "conflicting", "not_applicable"}
EVIDENCE_KINDS = {"file", "artifact", "run", "decision", "external"}
GATE_STATES = {"PASS", "FAIL", "UNKNOWN", "NA"}
GATE_CATEGORIES = {
    "data_provenance",
    "design_and_sampling",
    "unit_and_replication",
    "measurement_quality",
    "missingness_and_censoring",
    "multiplicity_and_selection",
    "robustness_and_sensitivity",
    "computational_reproducibility",
    "result_integrity",
    "claim_evidence",
    "validation",
    "data_leakage",
    "model_lock_and_evaluation",
    "calibration",
    "external_validity",
    "causal_identification",
    "temporality",
    "confounding_and_exchangeability",
    "positivity_and_overlap",
    "causal_sensitivity",
    "perturbation_and_intervention",
    "alternative_explanations",
    "necessity_sufficiency_rescue",
    "transportability",
    "clinical_relevance",
    "decision_comparator",
    "clinical_utility",
    "prospective_evaluation",
    "safety_and_harms",
}
BASE_DATA_CATEGORIES = {
    "data_provenance",
    "design_and_sampling",
    "unit_and_replication",
    "measurement_quality",
    "missingness_and_censoring",
    "multiplicity_and_selection",
    "robustness_and_sensitivity",
    "computational_reproducibility",
}
DIMENSION_VALUES = {
    "data_relation": {
        "same_observations",
        "held_out_observations",
        "same_subjects_new_measurement",
        "independent_sampling_frame",
        "not_assessed",
        "not_applicable",
    },
    "collection_timing": {
        "existing_before_claim_lock",
        "collected_after_claim_lock",
        "not_assessed",
        "not_applicable",
    },
    "measurement_relation": {
        "same_measurement_process",
        "orthogonal_measurement_process",
        "not_assessed",
        "not_applicable",
    },
    "analysis_relation": {
        "same_implementation",
        "alternative_method_same_team",
        "independent_implementation",
        "not_assessed",
        "not_applicable",
    },
    "evaluation_blinding": {
        "unblinded",
        "blinded_to_outcome_or_label",
        "not_assessed",
        "not_applicable",
    },
}
CLAIM_KEYS = {
    "claim_id",
    "statement",
    "claim_class",
    "source_ids",
    "estimand",
    "population",
    "contrast",
    "outcome",
    "time_frame",
}
BINDING_KEYS = {"path", "sha256"}


def validate_enum(
    value: Any,
    allowed: set[str],
    location: str,
    findings: list[dict[str, str]],
    code: str,
) -> None:
    if not is_string_enum(value, allowed):
        add_error(findings, code, location, f"Expected one of {sorted(allowed)}.")


def validate_id_list(
    value: Any,
    pattern: str,
    location: str,
    findings: list[dict[str, str]],
    *,
    allow_empty: bool,
) -> list[str]:
    values = validate_string_list(value, location, findings, allow_empty=allow_empty)
    if any(re.fullmatch(pattern, item) is None for item in values):
        add_error(findings, "scientific-id-list", location, "One or more IDs have invalid syntax.")
    return values


def validate_binding_shape(
    value: Any,
    location: str,
    findings: list[dict[str, str]],
    *,
    nullable: bool = False,
) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, dict):
        add_error(findings, "scientific-binding", location, "Expected a path/SHA-256 object.")
        return
    validate_keys(value, BINDING_KEYS, BINDING_KEYS, f"{location}.", findings)
    if not is_concrete_string(value.get("path")):
        add_error(findings, "scientific-binding-path", f"{location}.path", "Expected a concrete path.")
    if not valid_sha256(value.get("sha256")):
        add_error(findings, "scientific-binding-sha256", f"{location}.sha256", "Expected a lowercase SHA-256.")


def validate_claim(
    value: Any, location: str, findings: list[dict[str, str]]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        add_error(findings, "scientific-claim", location, "Expected an exact claim object.")
        return None
    validate_keys(value, CLAIM_KEYS, CLAIM_KEYS, f"{location}.", findings)
    for key in CLAIM_KEYS - {"claim_class", "source_ids"}:
        if not is_concrete_string(value.get(key)):
            add_error(findings, "scientific-claim-field", f"{location}.{key}", "Expected a concrete string.")
    if not isinstance(value.get("claim_id"), str) or re.fullmatch(
        r"CLM-[A-Za-z0-9][A-Za-z0-9._-]*", value["claim_id"]
    ) is None:
        add_error(findings, "scientific-claim-id", f"{location}.claim_id", "Invalid CLM-* identifier.")
    validate_enum(value.get("claim_class"), CLAIM_CLASSES, f"{location}.claim_class", findings, "scientific-claim-class")
    validate_id_list(value.get("source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.source_ids", findings, allow_empty=True)
    return value


def validate_source_roles(
    value: Any, location: str, findings: list[dict[str, str]]
) -> tuple[list[str], list[str]]:
    if not isinstance(value, dict):
        add_error(findings, "scientific-source-roles", location, "Expected a source-role object.")
        return [], []
    keys = {"primary_source_ids", "independent_validation_source_ids"}
    validate_keys(value, keys, keys, f"{location}.", findings)
    primary = validate_id_list(
        value.get("primary_source_ids"),
        r"SRC-[0-9A-F]{16}",
        f"{location}.primary_source_ids",
        findings,
        allow_empty=True,
    )
    validation = validate_id_list(
        value.get("independent_validation_source_ids"),
        r"SRC-[0-9A-F]{16}",
        f"{location}.independent_validation_source_ids",
        findings,
        allow_empty=True,
    )
    overlap = sorted(set(primary) & set(validation))
    if overlap:
        add_error(findings, "scientific-source-role-overlap", location, f"Primary and independent-validation source IDs overlap: {overlap}.")
    return primary, validation


def validate_dimensions(
    value: Any, location: str, findings: list[dict[str, str]]
) -> dict[str, str]:
    if not isinstance(value, dict):
        add_error(findings, "scientific-validation-dimensions", location, "Expected a complete dimension profile.")
        return {}
    validate_keys(value, set(DIMENSION_VALUES), set(DIMENSION_VALUES), f"{location}.", findings)
    result: dict[str, str] = {}
    for key, allowed in DIMENSION_VALUES.items():
        candidate = value.get(key)
        validate_enum(candidate, allowed, f"{location}.{key}", findings, "scientific-validation-dimension")
        if isinstance(candidate, str):
            result[key] = candidate
    return result


def required_gate_categories(
    purpose: Any,
    data_requirement: Any,
    analysis_mode: Any,
    claim_class: Any,
    has_validation_minimum: bool,
) -> set[str]:
    required = set(BASE_DATA_CATEGORIES if data_requirement == "data_bearing" else {"computational_reproducibility"})
    if purpose in NON_EXECUTION_PURPOSES:
        required.update({"result_integrity", "claim_evidence"})
    if has_validation_minimum:
        required.add("validation")
    if analysis_mode == "predictive" or claim_class == "prediction":
        required.update({"data_leakage", "model_lock_and_evaluation", "calibration", "external_validity"})
    if analysis_mode == "causal" or claim_class == "causal_effect":
        required.update({"causal_identification", "temporality", "confounding_and_exchangeability", "positivity_and_overlap", "causal_sensitivity"})
    if claim_class == "mechanism":
        required.update({"perturbation_and_intervention", "alternative_explanations", "necessity_sufficiency_rescue"})
    if claim_class == "translational":
        required.update({"external_validity", "transportability", "clinical_relevance"})
    if claim_class == "clinical_utility":
        required.update({"decision_comparator", "clinical_utility", "prospective_evaluation", "safety_and_harms"})
    if purpose == "decision_support":
        required.add("decision_comparator")
    return required


def validate_planned_validation(
    value: Any,
    index: int,
    all_source_ids: set[str],
    primary_source_ids: set[str],
    independent_source_ids: set[str],
    independent_unit: Any,
    findings: list[dict[str, str]],
) -> dict[str, Any] | None:
    location = f"analysis_spec.planned_validations[{index}]"
    keys = {
        "validation_id",
        "dimensions",
        "input_source_ids",
        "evaluation_source_ids",
        "partition_binding",
        "partition_unit",
        "success_criterion",
        "planned_evidence_kinds",
    }
    if not isinstance(value, dict):
        add_error(findings, "analysis-spec-planned-validation", location, "Expected an object.")
        return None
    validate_keys(value, keys, keys, f"{location}.", findings)
    validation_id = value.get("validation_id")
    if not isinstance(validation_id, str) or re.fullmatch(
        r"PV-[A-Za-z0-9][A-Za-z0-9._-]*", validation_id
    ) is None:
        add_error(findings, "analysis-spec-planned-validation-id", f"{location}.validation_id", "Invalid PV-* identifier.")
    dimensions = validate_dimensions(value.get("dimensions"), f"{location}.dimensions", findings)
    input_ids = validate_id_list(
        value.get("input_source_ids"),
        r"SRC-[0-9A-F]{16}",
        f"{location}.input_source_ids",
        findings,
        allow_empty=False,
    )
    evaluation_ids = validate_id_list(
        value.get("evaluation_source_ids"),
        r"SRC-[0-9A-F]{16}",
        f"{location}.evaluation_source_ids",
        findings,
        allow_empty=False,
    )
    if not set(input_ids) <= all_source_ids:
        add_error(findings, "analysis-spec-planned-source-scope", f"{location}.input_source_ids", "Planned validation inputs are outside the analysis source set.")
    if not set(evaluation_ids) <= set(input_ids):
        add_error(findings, "analysis-spec-planned-evaluation-scope", f"{location}.evaluation_source_ids", "Evaluation source IDs must be a subset of validation inputs.")
    relation = dimensions.get("data_relation")
    if relation == "same_observations" and not set(evaluation_ids) <= primary_source_ids:
        add_error(findings, "analysis-spec-planned-source-relation", f"{location}.evaluation_source_ids", "same_observations must evaluate primary sources.")
    if relation in {"independent_sampling_frame", "same_subjects_new_measurement"} and not set(evaluation_ids) <= independent_source_ids:
        add_error(findings, "analysis-spec-planned-source-relation", f"{location}.evaluation_source_ids", "This data relation requires independent-validation source IDs.")
    partition_binding = value.get("partition_binding")
    validate_binding_shape(partition_binding, f"{location}.partition_binding", findings, nullable=True)
    partition_unit = value.get("partition_unit")
    if relation == "held_out_observations":
        if partition_binding is None:
            add_error(findings, "analysis-spec-held-out-partition", f"{location}.partition_binding", "Held-out validation requires a hash-bound partition.")
        if partition_unit != independent_unit:
            add_error(findings, "analysis-spec-held-out-unit", f"{location}.partition_unit", "Held-out partitioning must occur at the declared independent unit.")
    elif partition_unit is not None and not is_concrete_string(partition_unit):
        add_error(findings, "analysis-spec-partition-unit", f"{location}.partition_unit", "Expected a concrete string or null.")
    if not is_concrete_string(value.get("success_criterion")):
        add_error(findings, "analysis-spec-validation-criterion", f"{location}.success_criterion", "Expected a prespecified concrete criterion.")
    evidence_kinds = validate_string_list(
        value.get("planned_evidence_kinds"),
        f"{location}.planned_evidence_kinds",
        findings,
        allow_empty=False,
    )
    invalid_kinds = sorted(set(evidence_kinds) - EVIDENCE_KINDS)
    if invalid_kinds:
        add_error(findings, "analysis-spec-validation-evidence-kind", f"{location}.planned_evidence_kinds", f"Invalid evidence kinds: {invalid_kinds}.")
    return value


def validate_spec_document(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    keys = {
        "schema_version",
        "analysis_id",
        "scope_id",
        "readiness_purpose",
        "question",
        "intended_use",
        "study_type",
        "data_requirement",
        "analysis_mode",
        "claim",
        "source_roles",
        "input_source_ids",
        "design",
        "prespecification",
        "planned_validations",
        "domain",
        "domain_spec",
        "backend_revision",
        "entry_points",
        "domain_parameters",
        "created_at",
    }
    validate_keys(document, keys, keys, "analysis_spec.", findings)
    if document.get("schema_version") != SPEC_SCHEMA:
        add_error(findings, "analysis-spec-schema", "analysis_spec.schema_version", f"Expected {SPEC_SCHEMA}.")
    for key in ("analysis_id", "scope_id", "question", "intended_use", "study_type", "domain"):
        if not is_concrete_string(document.get(key)):
            add_error(findings, "analysis-spec-field", f"analysis_spec.{key}", "Expected a concrete string.")
    validate_enum(document.get("readiness_purpose"), PURPOSES, "analysis_spec.readiness_purpose", findings, "analysis-spec-purpose")
    validate_enum(document.get("data_requirement"), DATA_REQUIREMENTS, "analysis_spec.data_requirement", findings, "analysis-spec-data-requirement")
    validate_enum(document.get("analysis_mode"), ANALYSIS_MODES, "analysis_spec.analysis_mode", findings, "analysis-spec-mode")
    claim = validate_claim(document.get("claim"), "analysis_spec.claim", findings)
    primary_ids, independent_ids = validate_source_roles(document.get("source_roles"), "analysis_spec.source_roles", findings)
    input_ids = validate_id_list(
        document.get("input_source_ids"),
        r"SRC-[0-9A-F]{16}",
        "analysis_spec.input_source_ids",
        findings,
        allow_empty=document.get("data_requirement") == "none",
    )
    if set(input_ids) != set(primary_ids) | set(independent_ids):
        add_error(findings, "analysis-spec-source-role-closure", "analysis_spec.input_source_ids", "Input source IDs must exactly equal the union of primary and independent-validation roles.")
    if document.get("data_requirement") == "data_bearing" and not primary_ids:
        add_error(findings, "analysis-spec-primary-source-required", "analysis_spec.source_roles.primary_source_ids", "A data-bearing analysis requires primary source IDs.")
    if document.get("data_requirement") == "none" and (input_ids or primary_ids or independent_ids):
        add_error(findings, "analysis-spec-source-not-applicable", "analysis_spec.source_roles", "A data-free analysis cannot declare source IDs.")
    if claim is not None and not set(claim.get("source_ids", [])) <= set(input_ids):
        add_error(findings, "analysis-spec-claim-source-scope", "analysis_spec.claim.source_ids", "Claim source IDs must be a subset of analysis inputs.")

    design = document.get("design")
    design_keys = {
        "population",
        "sampling_unit",
        "allocation_unit",
        "independent_unit",
        "analysis_unit",
        "observation_unit",
        "unit_hierarchy",
        "n_independent_units",
        "unit_map",
        "analysis_set_manifest",
        "cluster_variables",
        "repeated_measures",
        "pairing_variables",
        "correlation_handling",
        "exposure_or_intervention",
        "comparator",
        "outcome",
        "time_zero",
        "follow_up_window",
        "effect_measure",
        "missing_data",
        "multiplicity",
        "decision_rule",
        "protocol_deviation_status",
        "deviation_log",
    }
    independent_unit: Any = None
    design_blocker = False
    if not isinstance(design, dict):
        add_error(findings, "analysis-spec-design", "analysis_spec.design", "Expected a structured design object.")
    else:
        validate_keys(design, design_keys, design_keys, "analysis_spec.design.", findings)
        string_fields = {
            "population",
            "sampling_unit",
            "allocation_unit",
            "independent_unit",
            "analysis_unit",
            "observation_unit",
            "correlation_handling",
            "exposure_or_intervention",
            "comparator",
            "outcome",
            "time_zero",
            "follow_up_window",
            "effect_measure",
            "decision_rule",
        }
        for key in string_fields:
            if not is_concrete_string(design.get(key)):
                add_error(findings, "analysis-spec-design-field", f"analysis_spec.design.{key}", "Expected a concrete string.")
        independent_unit = design.get("independent_unit")
        hierarchy = validate_string_list(design.get("unit_hierarchy"), "analysis_spec.design.unit_hierarchy", findings, allow_empty=False)
        if hierarchy and (hierarchy[0] != independent_unit or hierarchy[-1] != design.get("observation_unit")):
            add_error(findings, "analysis-spec-unit-hierarchy", "analysis_spec.design.unit_hierarchy", "Unit hierarchy must run from independent unit to observation unit.")
        count = design.get("n_independent_units")
        if document.get("data_requirement") == "data_bearing" and (type(count) is not int or count < 1):
            add_error(findings, "analysis-spec-independent-unit-count", "analysis_spec.design.n_independent_units", "A data-bearing analysis requires a positive independent-unit count.")
        for key in ("unit_map", "analysis_set_manifest"):
            validate_binding_shape(design.get(key), f"analysis_spec.design.{key}", findings, nullable=document.get("data_requirement") == "none")
            if document.get("data_requirement") == "data_bearing" and design.get(key) is None:
                add_error(findings, "analysis-spec-design-binding", f"analysis_spec.design.{key}", "A data-bearing analysis requires this binding.")
        for key in ("cluster_variables", "pairing_variables"):
            validate_string_list(design.get(key), f"analysis_spec.design.{key}", findings, allow_empty=True)
        if type(design.get("repeated_measures")) is not bool:
            add_error(findings, "analysis-spec-repeated-measures", "analysis_spec.design.repeated_measures", "Expected a boolean.")
        missing = design.get("missing_data")
        missing_keys = {"variables", "mechanism_assumptions", "primary_strategy", "sensitivity_analyses"}
        if not isinstance(missing, dict):
            add_error(findings, "analysis-spec-missing-data", "analysis_spec.design.missing_data", "Expected a structured missing-data plan.")
        else:
            validate_keys(missing, missing_keys, missing_keys, "analysis_spec.design.missing_data.", findings)
            validate_string_list(missing.get("variables"), "analysis_spec.design.missing_data.variables", findings, allow_empty=True)
            validate_string_list(missing.get("sensitivity_analyses"), "analysis_spec.design.missing_data.sensitivity_analyses", findings, allow_empty=True)
            for key in ("mechanism_assumptions", "primary_strategy"):
                if not is_concrete_string(missing.get(key)):
                    add_error(findings, "analysis-spec-missing-data", f"analysis_spec.design.missing_data.{key}", "Expected a concrete string.")
        multiplicity = design.get("multiplicity")
        multiplicity_keys = {"families", "planned_hypothesis_count", "error_rate_target", "method", "selection_handling"}
        if not isinstance(multiplicity, dict):
            add_error(findings, "analysis-spec-multiplicity", "analysis_spec.design.multiplicity", "Expected a structured multiplicity plan.")
        else:
            validate_keys(multiplicity, multiplicity_keys, multiplicity_keys, "analysis_spec.design.multiplicity.", findings)
            validate_string_list(multiplicity.get("families"), "analysis_spec.design.multiplicity.families", findings, allow_empty=False)
            hypothesis_count = multiplicity.get("planned_hypothesis_count")
            if hypothesis_count is not None and (type(hypothesis_count) is not int or hypothesis_count < 1):
                add_error(findings, "analysis-spec-hypothesis-count", "analysis_spec.design.multiplicity.planned_hypothesis_count", "Expected a positive integer or null.")
            for key in ("error_rate_target", "method", "selection_handling"):
                if not is_concrete_string(multiplicity.get(key)):
                    add_error(findings, "analysis-spec-multiplicity", f"analysis_spec.design.multiplicity.{key}", "Expected a concrete string.")
        validate_enum(design.get("protocol_deviation_status"), {"none", "documented", "unresolved"}, "analysis_spec.design.protocol_deviation_status", findings, "analysis-spec-deviation-status")
        validate_binding_shape(design.get("deviation_log"), "analysis_spec.design.deviation_log", findings, nullable=True)
        if design.get("protocol_deviation_status") == "documented" and design.get("deviation_log") is None:
            add_error(findings, "analysis-spec-deviation-log", "analysis_spec.design.deviation_log", "Documented deviations require a bound log.")
        if design.get("protocol_deviation_status") == "unresolved":
            design_blocker = True
        if claim is not None:
            for claim_key, design_key in (("population", "population"), ("outcome", "outcome"), ("time_frame", "follow_up_window")):
                if claim.get(claim_key) != design.get(design_key):
                    add_error(findings, "analysis-spec-claim-design-mismatch", f"analysis_spec.claim.{claim_key}", f"Claim {claim_key} must exactly match design.{design_key}.")

    prespecification = document.get("prespecification")
    prespec_keys = {"status", "protocol", "locked_at", "first_data_access_at", "unblinded_at"}
    prespec_times: dict[str, datetime | None] = {}
    if not isinstance(prespecification, dict):
        add_error(findings, "analysis-spec-prespecification", "analysis_spec.prespecification", "Expected a structured prespecification record.")
    else:
        validate_keys(prespecification, prespec_keys, prespec_keys, "analysis_spec.prespecification.", findings)
        validate_enum(prespecification.get("status"), {"preregistered", "prespecified_not_preregistered", "post_hoc", "not_applicable"}, "analysis_spec.prespecification.status", findings, "analysis-spec-prespecification")
        validate_binding_shape(prespecification.get("protocol"), "analysis_spec.prespecification.protocol", findings, nullable=True)
        for key in ("locked_at", "first_data_access_at", "unblinded_at"):
            raw = prespecification.get(key)
            if raw is None:
                prespec_times[key] = None
                continue
            try:
                prespec_times[key] = parse_rfc3339(raw)
            except ContractError as exc:
                prespec_times[key] = None
                add_error(findings, "analysis-spec-prespecification-time", f"analysis_spec.prespecification.{key}", str(exc))
        if prespecification.get("status") in {"preregistered", "prespecified_not_preregistered"}:
            if prespecification.get("protocol") is None or prespec_times.get("locked_at") is None:
                add_error(findings, "analysis-spec-prespecification-binding", "analysis_spec.prespecification", "Prespecified analyses require a protocol binding and lock time.")
            locked = prespec_times.get("locked_at")
            for key in ("first_data_access_at", "unblinded_at"):
                later = prespec_times.get(key)
                if locked and later and locked > later:
                    add_error(findings, "analysis-spec-prespecification-order", f"analysis_spec.prespecification.{key}", "Protocol lock must not occur after data access or unblinding.")
        if document.get("analysis_mode") == "confirmatory" and prespecification.get("status") not in {"preregistered", "prespecified_not_preregistered"}:
            design_blocker = True

    planned_value = document.get("planned_validations")
    planned_map: dict[str, dict[str, Any]] = {}
    if not isinstance(planned_value, list):
        add_error(findings, "analysis-spec-planned-validations", "analysis_spec.planned_validations", "Expected a list.")
    else:
        for index, item in enumerate(planned_value):
            validated = validate_planned_validation(item, index, set(input_ids), set(primary_ids), set(independent_ids), independent_unit, findings)
            if validated is None:
                continue
            validation_id = validated.get("validation_id")
            if isinstance(validation_id, str):
                if validation_id in planned_map:
                    add_error(findings, "analysis-spec-planned-validation-duplicate", f"analysis_spec.planned_validations[{index}].validation_id", "Duplicate planned validation ID.")
                else:
                    planned_map[validation_id] = validated

    validate_binding_shape(document.get("domain_spec"), "analysis_spec.domain_spec", findings, nullable=document.get("data_requirement") == "none")
    if document.get("data_requirement") == "data_bearing" and document.get("domain_spec") is None:
        add_error(findings, "analysis-spec-domain-spec", "analysis_spec.domain_spec", "A data-bearing analysis requires a domain-specific spec binding.")
    backend = document.get("backend_revision")
    if backend is not None and not is_concrete_string(backend):
        add_error(findings, "analysis-spec-backend", "analysis_spec.backend_revision", "Expected a concrete string or null.")
    entry_points = validate_string_list(document.get("entry_points"), "analysis_spec.entry_points", findings, allow_empty=False)
    for index, entry_point in enumerate(entry_points):
        try:
            portable_project_relative(entry_point)
        except ContractError as exc:
            add_error(findings, "analysis-spec-entry-point", f"analysis_spec.entry_points[{index}]", str(exc))
    parameters = document.get("domain_parameters")
    if not isinstance(parameters, dict) or (document.get("data_requirement") == "data_bearing" and not parameters):
        add_error(findings, "analysis-spec-domain-parameters", "analysis_spec.domain_parameters", "A data-bearing analysis requires a non-empty parameter object.")
    try:
        created_at = parse_rfc3339(document.get("created_at"))
    except ContractError as exc:
        created_at = None
        add_error(findings, "analysis-spec-created-at", "analysis_spec.created_at", str(exc))
    locked_at = prespec_times.get("locked_at")
    if created_at and locked_at and created_at > locked_at:
        add_error(
            findings,
            "analysis-spec-lock-precedes-document",
            "analysis_spec.prespecification.locked_at",
            "The declared protocol lock cannot predate creation of the bound analysis spec.",
        )

    mode = document.get("analysis_mode")
    claim_class = claim.get("claim_class") if claim else None
    if mode == "descriptive" and claim_class != "observation":
        add_error(findings, "analysis-spec-mode-claim", "analysis_spec.claim.claim_class", "Descriptive mode can support observation claims only.")
    if claim_class == "prediction" and mode != "predictive":
        add_error(findings, "analysis-spec-mode-claim", "analysis_spec.claim.claim_class", "Prediction claims require predictive mode.")
    if claim_class in {"causal_effect", "mechanism"} and mode != "causal":
        add_error(findings, "analysis-spec-mode-claim", "analysis_spec.claim.claim_class", "Causal-effect and mechanism claims require causal mode.")
    if claim_class == "clinical_utility" and mode not in {"predictive", "causal"}:
        add_error(findings, "analysis-spec-mode-claim", "analysis_spec.claim.claim_class", "Clinical-utility claims require predictive or causal mode.")
    return {
        "document": document,
        "claim": claim,
        "input_source_ids": input_ids,
        "primary_source_ids": primary_ids,
        "independent_source_ids": independent_ids,
        "entry_points": entry_points,
        "planned_map": planned_map,
        "created_at": created_at,
        "design_blocker": design_blocker,
        "prespec_times": prespec_times,
        "plan_lock_time": locked_at,
    }, findings


def validate_minimum_requirement(
    value: Any,
    authorization_location: str,
    index: int,
    findings: list[dict[str, str]],
) -> dict[str, Any] | None:
    location = f"{authorization_location}.minimum_validation_requirements[{index}]"
    keys = {
        "requirement_id",
        "dimension_constraints",
        "required_evidence_kinds",
        "must_be_planned",
    }
    if not isinstance(value, dict):
        add_error(findings, "policy-validation-requirement", location, "Expected an object.")
        return None
    validate_keys(value, keys, keys, f"{location}.", findings)
    requirement_id = value.get("requirement_id")
    if not isinstance(requirement_id, str) or re.fullmatch(
        r"MIN-[A-Za-z0-9][A-Za-z0-9._-]*", requirement_id
    ) is None:
        add_error(findings, "policy-validation-requirement-id", f"{location}.requirement_id", "Invalid MIN-* identifier.")
    constraints = value.get("dimension_constraints")
    if not isinstance(constraints, dict) or not constraints:
        add_error(findings, "policy-validation-constraints", f"{location}.dimension_constraints", "Expected one or more dimension constraints.")
    else:
        validate_keys(constraints, set(DIMENSION_VALUES), set(), f"{location}.dimension_constraints.", findings)
        for dimension, accepted in constraints.items():
            values = validate_string_list(accepted, f"{location}.dimension_constraints.{dimension}", findings, allow_empty=False)
            allowed = DIMENSION_VALUES.get(dimension, set()) - {"not_assessed"}
            invalid = sorted(set(values) - allowed)
            if invalid:
                add_error(findings, "policy-validation-constraint-value", f"{location}.dimension_constraints.{dimension}", f"Invalid or non-assessable values: {invalid}.")
    evidence_kinds = validate_string_list(value.get("required_evidence_kinds"), f"{location}.required_evidence_kinds", findings, allow_empty=False)
    invalid_kinds = sorted(set(evidence_kinds) - EVIDENCE_KINDS)
    if invalid_kinds:
        add_error(findings, "policy-validation-evidence-kind", f"{location}.required_evidence_kinds", f"Invalid evidence kinds: {invalid_kinds}.")
    if type(value.get("must_be_planned")) is not bool:
        add_error(findings, "policy-validation-must-be-planned", f"{location}.must_be_planned", "Expected a boolean.")
    return value


def validate_policy_document_v2(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    keys = {
        "schema_version",
        "policy_id",
        "version",
        "assessor",
        "domain",
        "applicable_study_types",
        "applicable_data_requirements",
        "applicable_readiness_purposes",
        "methodological_basis",
        "authorizations",
        "gates",
    }
    validate_keys(document, keys, keys, "gate_policy.", findings)
    if document.get("schema_version") != POLICY_SCHEMA:
        add_error(findings, "policy-schema", "gate_policy.schema_version", f"Expected {POLICY_SCHEMA}.")
    for key in ("policy_id", "version", "domain"):
        if not is_concrete_string(document.get(key)):
            add_error(findings, "policy-field", f"gate_policy.{key}", "Expected a concrete string.")
    assessor = document.get("assessor")
    if not isinstance(assessor, dict):
        add_error(findings, "policy-assessor", "gate_policy.assessor", "Expected name/version object.")
    else:
        validate_keys(assessor, {"name", "version"}, {"name", "version"}, "gate_policy.assessor.", findings)
        for key in ("name", "version"):
            if not is_concrete_string(assessor.get(key)):
                add_error(findings, "policy-assessor", f"gate_policy.assessor.{key}", "Expected a concrete string.")
    validate_string_list(document.get("applicable_study_types"), "gate_policy.applicable_study_types", findings, allow_empty=False)
    requirements = validate_string_list(document.get("applicable_data_requirements"), "gate_policy.applicable_data_requirements", findings, allow_empty=False, allowed_literals={"none"})
    if set(requirements) - DATA_REQUIREMENTS:
        add_error(findings, "policy-data-requirement", "gate_policy.applicable_data_requirements", "Invalid data requirement.")
    purposes = validate_string_list(document.get("applicable_readiness_purposes"), "gate_policy.applicable_readiness_purposes", findings, allow_empty=False)
    if set(purposes) - PURPOSES:
        add_error(findings, "policy-purpose", "gate_policy.applicable_readiness_purposes", "Invalid readiness purpose.")
    validate_string_list(document.get("methodological_basis"), "gate_policy.methodological_basis", findings, allow_empty=False)

    authorizations_value = document.get("authorizations")
    authorization_map: dict[str, dict[str, Any]] = {}
    if not isinstance(authorizations_value, list) or not authorizations_value:
        add_error(findings, "policy-authorizations", "gate_policy.authorizations", "Expected at least one purpose authorization.")
        authorizations_value = []
    authorization_keys = {
        "authorization_id",
        "readiness_purpose",
        "analysis_mode",
        "claim_class",
        "required_claim_evidence_kinds",
        "minimum_validation_requirements",
    }
    for index, authorization in enumerate(authorizations_value):
        location = f"gate_policy.authorizations[{index}]"
        if not isinstance(authorization, dict):
            add_error(findings, "policy-authorization", location, "Expected an object.")
            continue
        validate_keys(authorization, authorization_keys, authorization_keys, f"{location}.", findings)
        authorization_id = authorization.get("authorization_id")
        if not isinstance(authorization_id, str) or re.fullmatch(
            r"AUTH-[A-Za-z0-9][A-Za-z0-9._-]*", authorization_id
        ) is None:
            add_error(findings, "policy-authorization-id", f"{location}.authorization_id", "Invalid AUTH-* identifier.")
        elif authorization_id in authorization_map:
            add_error(findings, "policy-authorization-duplicate", f"{location}.authorization_id", "Duplicate authorization ID.")
        else:
            authorization_map[authorization_id] = authorization
        validate_enum(authorization.get("readiness_purpose"), PURPOSES, f"{location}.readiness_purpose", findings, "policy-authorization-purpose")
        validate_enum(authorization.get("analysis_mode"), ANALYSIS_MODES, f"{location}.analysis_mode", findings, "policy-authorization-mode")
        validate_enum(authorization.get("claim_class"), CLAIM_CLASSES, f"{location}.claim_class", findings, "policy-authorization-claim")
        evidence_kinds = validate_string_list(authorization.get("required_claim_evidence_kinds"), f"{location}.required_claim_evidence_kinds", findings, allow_empty=authorization.get("readiness_purpose") == "analysis_execution")
        invalid_kinds = sorted(set(evidence_kinds) - EVIDENCE_KINDS)
        if invalid_kinds:
            add_error(findings, "policy-claim-evidence-kind", f"{location}.required_claim_evidence_kinds", f"Invalid evidence kinds: {invalid_kinds}.")
        if authorization.get("readiness_purpose") == "analysis_execution" and evidence_kinds:
            add_error(findings, "policy-execution-claim-evidence", f"{location}.required_claim_evidence_kinds", "Execution readiness cannot require or imply current claim evidence.")
        if authorization.get("readiness_purpose") in NON_EXECUTION_PURPOSES and not {"run", "artifact"} <= set(evidence_kinds):
            add_error(findings, "policy-claim-evidence-floor", f"{location}.required_claim_evidence_kinds", "Post-result purposes require both run and artifact evidence.")
        if authorization.get("readiness_purpose") == "decision_support" and "decision" not in evidence_kinds:
            add_error(findings, "policy-decision-evidence-floor", f"{location}.required_claim_evidence_kinds", "Decision support requires decision evidence.")
        minima_value = authorization.get("minimum_validation_requirements")
        if not isinstance(minima_value, list):
            add_error(findings, "policy-validation-requirements", f"{location}.minimum_validation_requirements", "Expected a list.")
            continue
        seen_requirements: set[str] = set()
        for req_index, requirement in enumerate(minima_value):
            validated = validate_minimum_requirement(requirement, location, req_index, findings)
            if validated and isinstance(validated.get("requirement_id"), str):
                requirement_id = validated["requirement_id"]
                if requirement_id in seen_requirements:
                    add_error(findings, "policy-validation-requirement-duplicate", f"{location}.minimum_validation_requirements[{req_index}]", "Duplicate requirement ID within authorization.")
                seen_requirements.add(requirement_id)

    gates_value = document.get("gates")
    gate_map: dict[str, dict[str, Any]] = {}
    if not isinstance(gates_value, list) or not gates_value:
        add_error(findings, "policy-gates", "gate_policy.gates", "Expected at least one gate.")
        gates_value = []
    gate_keys = {
        "gate_id",
        "gate_category",
        "required_for_ready",
        "allow_na",
        "requirement",
        "applicability",
        "evaluation_method",
        "pass_condition",
        "required_evidence_kinds",
        "failure_effect",
    }
    for index, gate in enumerate(gates_value):
        location = f"gate_policy.gates[{index}]"
        if not isinstance(gate, dict):
            add_error(findings, "policy-gate", location, "Expected an object.")
            continue
        validate_keys(gate, gate_keys, gate_keys, f"{location}.", findings)
        gate_id = gate.get("gate_id")
        if not is_concrete_string(gate_id):
            add_error(findings, "policy-gate-id", f"{location}.gate_id", "Expected a concrete gate ID.")
        elif gate_id in gate_map:
            add_error(findings, "policy-gate-duplicate", f"{location}.gate_id", "Duplicate gate ID.")
        else:
            gate_map[gate_id] = gate
        validate_enum(gate.get("gate_category"), GATE_CATEGORIES, f"{location}.gate_category", findings, "policy-gate-category")
        for key in ("requirement", "applicability", "evaluation_method", "pass_condition"):
            if not is_concrete_string(gate.get(key)):
                add_error(findings, "policy-gate-field", f"{location}.{key}", "Expected a concrete string.")
        for key in ("required_for_ready", "allow_na"):
            if type(gate.get(key)) is not bool:
                add_error(findings, "policy-gate-boolean", f"{location}.{key}", "Expected a boolean.")
        expected_effect = "block" if gate.get("required_for_ready") is True else "review"
        if gate.get("failure_effect") != expected_effect:
            add_error(findings, "policy-gate-failure-effect", f"{location}.failure_effect", f"Expected {expected_effect} for this requiredness.")
        evidence_kinds = validate_string_list(gate.get("required_evidence_kinds"), f"{location}.required_evidence_kinds", findings, allow_empty=False)
        if set(evidence_kinds) - EVIDENCE_KINDS:
            add_error(findings, "policy-gate-evidence-kind", f"{location}.required_evidence_kinds", "Invalid evidence kind.")
        has_post_result_authorization = any(
            item.get("readiness_purpose") in NON_EXECUTION_PURPOSES
            for item in authorization_map.values()
        )
        if (
            has_post_result_authorization
            and gate.get("gate_category")
            in {"result_integrity", "claim_evidence", "validation"}
            and gate.get("required_for_ready") is True
            and not {"run", "artifact"} <= set(evidence_kinds)
        ):
            add_error(findings, "policy-gate-evidence-floor", f"{location}.required_evidence_kinds", "Required post-result scientific gates must require run and artifact evidence.")
    return {"document": document, "authorization_map": authorization_map, "gate_map": gate_map}, findings


def validate_environment_document(
    root: Path,
    document: dict[str, Any],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> tuple[str | None, str | None, list[str]]:
    keys = {
        "schema_version",
        "environment_id",
        "captured_at",
        "capture_method",
        "working_directory",
        "platform",
        "runtimes",
        "package_locks",
        "containers",
        "external_resources",
        "randomness",
    }
    validate_keys(document, keys, keys, "environment_manifest.", contract_findings)
    if document.get("schema_version") != ENVIRONMENT_SCHEMA:
        add_error(contract_findings, "environment-schema", "environment_manifest.schema_version", f"Expected {ENVIRONMENT_SCHEMA}.")
    environment_id = document.get("environment_id")
    if not is_concrete_string(environment_id):
        add_error(contract_findings, "environment-id", "environment_manifest.environment_id", "Expected a concrete environment ID.")
        environment_id = None
    try:
        captured_at = parse_rfc3339(document.get("captured_at"))
    except ContractError as exc:
        captured_at = None
        add_error(contract_findings, "environment-captured-at", "environment_manifest.captured_at", str(exc))
    if captured_at and assessed_at and captured_at > assessed_at + timedelta(minutes=5):
        add_error(contract_findings, "environment-after-assessment", "environment_manifest.captured_at", "Environment capture occurred after assessment.")
    if not is_concrete_string(document.get("capture_method")):
        add_error(contract_findings, "environment-capture-method", "environment_manifest.capture_method", "Expected a concrete capture method.")
    working_directory = document.get("working_directory")
    try:
        working_directory = portable_project_relative(working_directory)
    except ContractError as exc:
        working_directory = None
        add_error(contract_findings, "environment-working-directory", "environment_manifest.working_directory", str(exc))
    platform = document.get("platform")
    if not isinstance(platform, dict):
        add_error(contract_findings, "environment-platform", "environment_manifest.platform", "Expected an os/release/architecture object.")
    else:
        platform_keys = {"os", "release", "architecture"}
        validate_keys(platform, platform_keys, platform_keys, "environment_manifest.platform.", contract_findings)
        for key in platform_keys:
            if not is_concrete_string(platform.get(key)):
                add_error(contract_findings, "environment-platform", f"environment_manifest.platform.{key}", "Expected a concrete string.")
    runtimes = document.get("runtimes")
    runtime_names: list[str] = []
    if not isinstance(runtimes, list) or not runtimes:
        add_error(contract_findings, "environment-runtimes", "environment_manifest.runtimes", "Expected at least one runtime/version record.")
    else:
        for index, runtime in enumerate(runtimes):
            location = f"environment_manifest.runtimes[{index}]"
            if not isinstance(runtime, dict):
                add_error(contract_findings, "environment-runtime", location, "Expected a name/version object.")
                continue
            validate_keys(runtime, {"name", "version"}, {"name", "version"}, f"{location}.", contract_findings)
            for key in ("name", "version"):
                if not is_concrete_string(runtime.get(key)):
                    add_error(contract_findings, "environment-runtime", f"{location}.{key}", "Expected a concrete string.")
            if isinstance(runtime.get("name"), str):
                runtime_names.append(runtime["name"])
        if len(runtime_names) != len(set(runtime_names)):
            add_error(contract_findings, "environment-runtime-duplicate", "environment_manifest.runtimes", "Runtime names must be unique.")
    dependency_statuses: list[str] = []
    package_locks = document.get("package_locks")
    if not isinstance(package_locks, list):
        add_error(contract_findings, "environment-package-locks", "environment_manifest.package_locks", "Expected a list.")
        package_locks = []
    for index, lock in enumerate(package_locks):
        location = f"environment_manifest.package_locks[{index}]"
        if not isinstance(lock, dict):
            add_error(contract_findings, "environment-package-lock", location, "Expected path/SHA-256/format object.")
            continue
        validate_keys(lock, {"path", "sha256", "format"}, {"path", "sha256", "format"}, f"{location}.", contract_findings)
        if not is_concrete_string(lock.get("format")):
            add_error(contract_findings, "environment-package-lock-format", f"{location}.format", "Expected a concrete lock format.")
        status, _ = validate_binding(root, {"path": lock.get("path"), "sha256": lock.get("sha256")}, location, contract_findings, currency_findings)
        dependency_statuses.append(status)
    containers = document.get("containers")
    if not isinstance(containers, list):
        add_error(contract_findings, "environment-containers", "environment_manifest.containers", "Expected a list.")
        containers = []
    for index, container in enumerate(containers):
        location = f"environment_manifest.containers[{index}]"
        if not isinstance(container, dict):
            add_error(contract_findings, "environment-container", location, "Expected image/digest object.")
            continue
        validate_keys(container, {"image", "digest"}, {"image", "digest"}, f"{location}.", contract_findings)
        if not is_concrete_string(container.get("image")) or not isinstance(container.get("digest"), str) or re.fullmatch(r"sha256:[0-9a-f]{64}", container["digest"]) is None:
            add_error(contract_findings, "environment-container", location, "Container requires a concrete image and immutable sha256 digest.")
    if not package_locks and not containers:
        add_error(contract_findings, "environment-rebuild-anchor", "environment_manifest", "Environment requires at least one package lock or immutable container digest.")
    resources = document.get("external_resources")
    if not isinstance(resources, list):
        add_error(contract_findings, "environment-external-resources", "environment_manifest.external_resources", "Expected a list.")
    else:
        for index, resource in enumerate(resources):
            location = f"environment_manifest.external_resources[{index}]"
            if not isinstance(resource, dict):
                add_error(contract_findings, "environment-external-resource", location, "Expected name/version/reference object.")
                continue
            resource_keys = {"name", "version", "reference"}
            validate_keys(resource, resource_keys, resource_keys, f"{location}.", contract_findings)
            for key in resource_keys:
                if not is_concrete_string(resource.get(key)):
                    add_error(contract_findings, "environment-external-resource", f"{location}.{key}", "Expected a concrete string.")
    randomness = document.get("randomness")
    randomness_keys = {"seed_policy", "seeds", "deterministic_operations", "parallelism"}
    if not isinstance(randomness, dict):
        add_error(contract_findings, "environment-randomness", "environment_manifest.randomness", "Expected a randomness/parallelism object.")
    else:
        validate_keys(randomness, randomness_keys, randomness_keys, "environment_manifest.randomness.", contract_findings)
        for key in ("seed_policy", "deterministic_operations", "parallelism"):
            if not is_concrete_string(randomness.get(key)):
                add_error(contract_findings, "environment-randomness", f"environment_manifest.randomness.{key}", "Expected a concrete string.")
        if not isinstance(randomness.get("seeds"), dict):
            add_error(contract_findings, "environment-seeds", "environment_manifest.randomness.seeds", "Expected an object.")
    return environment_id, working_directory, dependency_statuses


def validate_invocation_document(
    root: Path,
    document: dict[str, Any],
    row: dict[str, str],
    environment_id: str | None,
    environment_working_directory: str | None,
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> None:
    run_id = row.get("run_id", "")
    location = f"run.{run_id}.invocation"
    keys = {
        "schema_version",
        "run_id",
        "captured_at",
        "argv",
        "working_directory",
        "environment_id",
        "config",
        "random_seeds",
        "parallelism",
        "scheduler",
        "notes",
    }
    validate_keys(document, keys, keys, f"{location}.", contract_findings)
    if document.get("schema_version") != INVOCATION_SCHEMA:
        add_error(contract_findings, "invocation-schema", f"{location}.schema_version", f"Expected {INVOCATION_SCHEMA}.")
    if document.get("run_id") != run_id:
        add_error(contract_findings, "invocation-run-id", f"{location}.run_id", "Invocation run ID does not match RUNS.tsv.")
    try:
        captured_at = parse_rfc3339(document.get("captured_at"))
    except ContractError as exc:
        captured_at = None
        add_error(contract_findings, "invocation-captured-at", f"{location}.captured_at", str(exc))
    try:
        started_at = parse_rfc3339(row.get("started_at"))
        completed_at = parse_rfc3339(row.get("completed_at"))
    except ContractError:
        started_at = completed_at = None
    if captured_at and started_at and captured_at < started_at - timedelta(minutes=5):
        add_error(contract_findings, "invocation-time-order", f"{location}.captured_at", "Invocation capture predates the run start.")
    if captured_at and completed_at and captured_at > completed_at + timedelta(minutes=5):
        add_error(contract_findings, "invocation-time-order", f"{location}.captured_at", "Invocation capture follows run completion.")
    if captured_at and assessed_at and captured_at > assessed_at + timedelta(minutes=5):
        add_error(contract_findings, "invocation-after-assessment", f"{location}.captured_at", "Invocation was captured after assessment.")
    argv = document.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item or "\x00" in item or "\n" in item for item in argv):
        add_error(contract_findings, "invocation-argv", f"{location}.argv", "Expected a non-empty control-free argv array.")
    elif row.get("entry_point") not in argv:
        add_error(contract_findings, "invocation-entry-point", f"{location}.argv", "argv must contain the registered entry point as an exact element.")
    try:
        working_directory = portable_project_relative(document.get("working_directory"))
    except ContractError as exc:
        working_directory = None
        add_error(contract_findings, "invocation-working-directory", f"{location}.working_directory", str(exc))
    if working_directory != environment_working_directory:
        add_error(contract_findings, "invocation-environment-cwd", f"{location}.working_directory", "Invocation and environment working directories differ.")
    if document.get("environment_id") != environment_id:
        add_error(contract_findings, "invocation-environment-id", f"{location}.environment_id", "Invocation environment ID does not match the bound environment manifest.")
    config = document.get("config")
    if row.get("config_path") == "not_applicable":
        if config is not None:
            add_error(contract_findings, "invocation-config", f"{location}.config", "Run declares config not applicable but invocation binds one.")
    else:
        expected_config = {"path": row.get("config_path"), "sha256": row.get("config_sha256")}
        if config != expected_config:
            add_error(contract_findings, "invocation-config", f"{location}.config", "Invocation config does not exactly match RUNS.tsv.")
        elif isinstance(config, dict):
            validate_binding(root, config, f"{location}.config", contract_findings, currency_findings)
    for key in ("random_seeds", "parallelism"):
        if not isinstance(document.get(key), dict):
            add_error(contract_findings, "invocation-runtime-setting", f"{location}.{key}", "Expected an object, empty only when genuinely not applicable.")
    if document.get("scheduler") is not None and not isinstance(document.get("scheduler"), dict):
        add_error(contract_findings, "invocation-scheduler", f"{location}.scheduler", "Expected an object or null.")
    validate_string_list(document.get("notes"), f"{location}.notes", contract_findings, allow_empty=True)


ARTIFACT_KINDS = {
    "source",
    "intermediate",
    "result",
    "validation",
    "report",
    "figure",
    "table",
    "log",
    "specification",
    "other",
}
ARTIFACT_PURPOSES = {
    "input",
    "output",
    "technical_validation",
    "scientific_validation",
    "claim_support",
    "not_applicable",
}


def load_artifact_registry(
    root: Path, findings: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    required_columns = {
        "artifact_id",
        "analysis_id",
        "path",
        "role",
        "artifact_kind",
        "evidence_purposes",
        "source_provenance_status",
        "source_ids",
        "parent_artifact_ids",
        "run_id",
        "sha256",
        "size_bytes",
        "recorded_at",
        "access_class",
        "license_or_agreement",
        "lifecycle_status",
    }
    try:
        path = resolve_project_relative(root, "provenance/ARTIFACTS.tsv", must_exist=True)
        if path.is_symlink() or not path.is_file():
            raise ContractError("Artifact registry must be a regular non-symlink file")
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None:
                raise ContractError("Artifact registry has no header")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ContractError("Artifact registry has duplicate headers")
            missing = sorted(required_columns - set(reader.fieldnames))
            if missing:
                raise ContractError(f"Artifact registry lacks v2 columns: {missing}")
            rows = list(reader)
            if any(None in row or any(not isinstance(item, str) for item in row.values()) for row in rows):
                raise ContractError("Artifact registry row width does not match its header")
    except (OSError, UnicodeError, csv.Error, ContractError) as exc:
        add_error(findings, "scientific-artifact-registry", "provenance/ARTIFACTS.tsv", str(exc))
        return {}
    result: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        artifact_id = row.get("artifact_id", "")
        if artifact_id in result:
            add_error(findings, "scientific-artifact-id-duplicate", f"provenance/ARTIFACTS.tsv[{index}]", f"Duplicate artifact ID {artifact_id!r}.")
        elif artifact_id:
            result[artifact_id] = row
    return result


def artifact_purposes(
    row: dict[str, str], location: str, findings: list[dict[str, str]]
) -> set[str]:
    raw = row.get("evidence_purposes", "")
    if not raw:
        add_error(findings, "scientific-artifact-purpose", location, "Artifact evidence_purposes is required.")
        return set()
    values = {item.strip() for item in raw.split(";")}
    invalid = sorted(values - ARTIFACT_PURPOSES)
    if invalid or "" in values:
        add_error(findings, "scientific-artifact-purpose", location, f"Invalid evidence purposes: {invalid}.")
    if "not_applicable" in values and len(values) != 1:
        add_error(findings, "scientific-artifact-purpose", location, "not_applicable cannot be combined with another evidence purpose.")
    return values


def close_artifact_lineage(
    root: Path,
    start_ids: set[str],
    artifact_rows: dict[str, dict[str, str]],
    analysis_id: Any,
    data_requirement: Any,
    assessed_source_ids: list[str],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> set[str]:
    closure: set[str] = set()
    visiting: set[str] = set()

    def visit(artifact_id: str) -> set[str]:
        if artifact_id in visiting:
            add_error(contract_findings, "scientific-artifact-lineage-cycle", artifact_id, "Artifact parent graph contains a cycle.")
            return set()
        if artifact_id in closure:
            row = artifact_rows.get(artifact_id, {})
            return set(parse_source_ids(row.get("source_ids"), f"artifact.{artifact_id}.source_ids", contract_findings, allow_empty=data_requirement == "none"))
        row = artifact_rows.get(artifact_id)
        if row is None:
            add_error(contract_findings, "scientific-artifact-parent-missing", artifact_id, "Artifact or parent ID is absent from ARTIFACTS.tsv.")
            return set()
        visiting.add(artifact_id)
        location = f"artifact.{artifact_id}"
        own_sources = set(
            validate_artifact_row(
                root,
                row,
                location,
                analysis_id,
                data_requirement,
                assessed_source_ids,
                assessed_at,
                contract_findings,
                currency_findings,
            )
        )
        if row.get("artifact_kind") not in ARTIFACT_KINDS:
            add_error(contract_findings, "scientific-artifact-kind", f"{location}.artifact_kind", f"Expected one of {sorted(ARTIFACT_KINDS)}.")
        artifact_purposes(row, f"{location}.evidence_purposes", contract_findings)
        raw_parents = row.get("parent_artifact_ids", "")
        parents = (
            parse_registry_ids(raw_parents, f"{location}.parent_artifact_ids", contract_findings)
            if raw_parents
            else []
        )
        if artifact_id in parents:
            add_error(contract_findings, "scientific-artifact-self-parent", f"{location}.parent_artifact_ids", "Artifact cannot parent itself.")
        parent_sources: set[str] = set()
        for parent_id in parents:
            parent_sources.update(visit(parent_id))
        if parents and own_sources != parent_sources:
            add_error(contract_findings, "scientific-artifact-source-propagation", f"{location}.source_ids", "Derived artifact source IDs must exactly equal the union of all parent source IDs.")
        visiting.remove(artifact_id)
        closure.add(artifact_id)
        return own_sources

    for artifact_id in sorted(start_ids):
        visit(artifact_id)
    return closure


def resolve_v2_run(
    root: Path,
    evidence: dict[str, Any],
    artifact_rows: dict[str, dict[str, str]],
    analysis_id: Any,
    data_requirement: Any,
    assessed_source_ids: list[str],
    assessed_at: datetime | None,
    environment_id: str | None,
    environment_working_directory: str | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> dict[str, Any] | None:
    run_id = evidence.get("ref")
    if not isinstance(run_id, str):
        return None
    row = registry_row(root, "provenance/RUNS.tsv", "run_id", run_id, f"run.{run_id}", contract_findings)
    if row is None:
        return None
    input_ids = set(parse_registry_ids(row.get("input_artifact_ids"), f"run.{run_id}.input_artifact_ids", contract_findings, allow_empty=data_requirement == "none"))
    output_ids = set(parse_registry_ids(row.get("output_artifact_ids"), f"run.{run_id}.output_artifact_ids", contract_findings))
    validation_ids = set(parse_registry_ids(row.get("validation_evidence_ids"), f"run.{run_id}.validation_evidence_ids", contract_findings))
    direct_ids = input_ids | output_ids | validation_ids
    closure = close_artifact_lineage(
        root,
        direct_ids,
        artifact_rows,
        analysis_id,
        data_requirement,
        assessed_source_ids,
        assessed_at,
        contract_findings,
        currency_findings,
    )
    lineage_hashes = evidence.get("lineage_record_sha256s")
    if not isinstance(lineage_hashes, dict):
        add_error(contract_findings, "scientific-run-lineage-records", f"run.{run_id}.lineage_record_sha256s", "Expected an artifact-ID to record-digest map.")
        lineage_hashes = {}
    if set(lineage_hashes) != closure:
        add_error(contract_findings, "scientific-run-lineage-records", f"run.{run_id}.lineage_record_sha256s", f"Lineage record map must exactly bind the transitive artifact closure: {sorted(closure)}.")
    for artifact_id in closure:
        digest = lineage_hashes.get(artifact_id)
        if not valid_sha256(digest) or digest != canonical_record_sha256(artifact_rows[artifact_id]):
            add_error(contract_findings, "scientific-run-lineage-record-stale", f"run.{run_id}.lineage_record_sha256s.{artifact_id}", "Lineage artifact-row digest is invalid or stale.")
    for artifact_id in input_ids:
        row_purposes = artifact_purposes(artifact_rows.get(artifact_id, {}), f"artifact.{artifact_id}.evidence_purposes", contract_findings)
        if "input" not in row_purposes:
            add_error(contract_findings, "scientific-run-artifact-purpose", artifact_id, "Run input artifact lacks the input evidence purpose.")
    for artifact_id in output_ids:
        row_purposes = artifact_purposes(artifact_rows.get(artifact_id, {}), f"artifact.{artifact_id}.evidence_purposes", contract_findings)
        if "output" not in row_purposes:
            add_error(contract_findings, "scientific-run-artifact-purpose", artifact_id, "Run output artifact lacks the output evidence purpose.")
    for artifact_id in validation_ids:
        row_purposes = artifact_purposes(artifact_rows.get(artifact_id, {}), f"artifact.{artifact_id}.evidence_purposes", contract_findings)
        if not {"technical_validation", "scientific_validation"} & row_purposes:
            add_error(contract_findings, "scientific-run-artifact-purpose", artifact_id, "Validation artifact lacks a validation evidence purpose.")
    invocation_binding = {"path": row.get("invocation_path"), "sha256": row.get("invocation_sha256")}
    invocation_status, invocation_path = validate_binding(root, invocation_binding, f"run.{run_id}.invocation", contract_findings, currency_findings)
    if invocation_status == "current" and invocation_path is not None:
        try:
            relative = portable_project_relative(row.get("invocation_path"))
            expected_parent = Path("analysis") / "runs" / run_id
            if expected_parent not in Path(relative).parents:
                raise ContractError("Invocation record must be inside analysis/runs/<run_id>/")
            invocation = load_json_object(invocation_path)
            validate_invocation_document(root, invocation, row, environment_id, environment_working_directory, assessed_at, contract_findings, currency_findings)
        except ContractError as exc:
            add_error(contract_findings, "scientific-invocation-read", f"run.{run_id}.invocation", str(exc))
    input_sources: set[str] = set()
    for artifact_id in input_ids:
        input_sources.update(parse_source_ids(artifact_rows.get(artifact_id, {}).get("source_ids"), f"artifact.{artifact_id}.source_ids", contract_findings, allow_empty=data_requirement == "none"))
    try:
        started_at = parse_rfc3339(row.get("started_at"))
    except ContractError:
        started_at = None
    return {
        "row": row,
        "input_ids": input_ids,
        "output_ids": output_ids,
        "validation_ids": validation_ids,
        "lineage_ids": closure,
        "input_source_ids": input_sources,
        "started_at": started_at,
    }


def validate_overlap_check(
    root: Path,
    binding: Any,
    record: dict[str, Any],
    spec: dict[str, Any],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> None:
    location = f"achieved_validation.{record.get('validation_id')}.unit_overlap_check"
    status, path = validate_binding(root, binding, location, contract_findings, currency_findings)
    if status != "current" or path is None:
        return
    try:
        document = load_json_object(path)
    except ContractError as exc:
        add_error(contract_findings, "scientific-overlap-check-read", location, str(exc))
        return
    keys = {
        "schema_version",
        "check_id",
        "created_at",
        "unit_type",
        "reference_source_ids",
        "evaluation_source_ids",
        "reference_unit_count",
        "evaluation_unit_count",
        "overlap_count",
        "method",
    }
    validate_keys(document, keys, keys, f"{location}.", contract_findings)
    if document.get("schema_version") != "research-unit-overlap/v1":
        add_error(contract_findings, "scientific-overlap-check-schema", f"{location}.schema_version", "Expected research-unit-overlap/v1.")
    for key in ("check_id", "unit_type", "method"):
        if not is_concrete_string(document.get(key)):
            add_error(contract_findings, "scientific-overlap-check-field", f"{location}.{key}", "Expected a concrete string.")
    expected_unit = spec.get("document", {}).get("design", {}).get("independent_unit")
    if document.get("unit_type") != expected_unit:
        add_error(contract_findings, "scientific-overlap-check-unit", f"{location}.unit_type", "Overlap check must use the declared independent unit.")
    reference_ids = validate_id_list(document.get("reference_source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.reference_source_ids", contract_findings, allow_empty=False)
    evaluation_ids = validate_id_list(document.get("evaluation_source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.evaluation_source_ids", contract_findings, allow_empty=False)
    if set(reference_ids) != set(spec.get("primary_source_ids", [])):
        add_error(contract_findings, "scientific-overlap-check-reference-sources", f"{location}.reference_source_ids", "Overlap check must bind all primary source IDs.")
    if set(evaluation_ids) != set(record.get("evaluation_source_ids", [])):
        add_error(contract_findings, "scientific-overlap-check-evaluation-sources", f"{location}.evaluation_source_ids", "Overlap check evaluation sources do not match the validation record.")
    for key in ("reference_unit_count", "evaluation_unit_count"):
        if type(document.get(key)) is not int or document[key] < 1:
            add_error(contract_findings, "scientific-overlap-check-count", f"{location}.{key}", "Expected a positive integer.")
    if document.get("overlap_count") != 0:
        add_error(contract_findings, "scientific-overlap-detected", f"{location}.overlap_count", "Held-out or independent validation requires zero overlapping independent units.")
    try:
        created_at = parse_rfc3339(document.get("created_at"))
    except ContractError as exc:
        add_error(contract_findings, "scientific-overlap-check-time", f"{location}.created_at", str(exc))
    else:
        if assessed_at and created_at > assessed_at + timedelta(minutes=5):
            add_error(contract_findings, "scientific-overlap-check-after-assessment", f"{location}.created_at", "Overlap check postdates the assessment.")


def validate_timing_check(
    root: Path,
    binding: Any,
    record: dict[str, Any],
    spec: dict[str, Any],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> None:
    location = f"achieved_validation.{record.get('validation_id')}.timing_check"
    status, path = validate_binding(root, binding, location, contract_findings, currency_findings)
    if status != "current" or path is None:
        return
    try:
        document = load_json_object(path)
    except ContractError as exc:
        add_error(contract_findings, "scientific-timing-check-read", location, str(exc))
        return
    keys = {
        "schema_version",
        "check_id",
        "created_at",
        "protocol_locked_at",
        "collection_started_at",
        "source_ids",
        "evidence_reference",
    }
    validate_keys(document, keys, keys, f"{location}.", contract_findings)
    if document.get("schema_version") != "research-timing-check/v1":
        add_error(contract_findings, "scientific-timing-check-schema", f"{location}.schema_version", "Expected research-timing-check/v1.")
    for key in ("check_id", "evidence_reference"):
        if not is_concrete_string(document.get(key)):
            add_error(contract_findings, "scientific-timing-check-field", f"{location}.{key}", "Expected a concrete string.")
    source_ids = validate_id_list(document.get("source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.source_ids", contract_findings, allow_empty=False)
    if set(source_ids) != set(record.get("evaluation_source_ids", [])):
        add_error(contract_findings, "scientific-timing-check-sources", f"{location}.source_ids", "Timing check source IDs do not match the validation record.")
    parsed: dict[str, datetime | None] = {}
    for key in ("created_at", "protocol_locked_at", "collection_started_at"):
        try:
            parsed[key] = parse_rfc3339(document.get(key))
        except ContractError as exc:
            parsed[key] = None
            add_error(contract_findings, "scientific-timing-check-time", f"{location}.{key}", str(exc))
    expected_lock = spec.get("prespec_times", {}).get("locked_at")
    if expected_lock is None or parsed.get("protocol_locked_at") != expected_lock:
        add_error(contract_findings, "scientific-timing-check-lock", f"{location}.protocol_locked_at", "Timing check must exactly bind the analysis protocol lock time.")
    if parsed.get("protocol_locked_at") and parsed.get("collection_started_at") and parsed["protocol_locked_at"] >= parsed["collection_started_at"]:
        add_error(contract_findings, "scientific-timing-order", location, "Prospective collection must start after protocol lock.")
    if assessed_at and parsed.get("created_at") and parsed["created_at"] > assessed_at + timedelta(minutes=5):
        add_error(contract_findings, "scientific-timing-check-after-assessment", f"{location}.created_at", "Timing check postdates the assessment.")


def validate_achieved_validation(
    root: Path,
    value: Any,
    index: int,
    spec: dict[str, Any],
    gate_map: dict[str, dict[str, Any]],
    run_info: dict[str, dict[str, Any]],
    artifact_rows: dict[str, dict[str, str]],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> dict[str, Any] | None:
    location = f"achieved_validations[{index}]"
    keys = {
        "validation_id",
        "planned_validation_id",
        "dimensions",
        "input_source_ids",
        "evaluation_source_ids",
        "evaluation_input_artifact_ids",
        "partition_binding",
        "partition_unit",
        "unit_overlap_check",
        "timing_check",
        "success_criterion",
        "outcome",
        "observed_result",
        "evidence_gate_ids",
    }
    if not isinstance(value, dict):
        add_error(contract_findings, "scientific-achieved-validation", location, "Expected an object.")
        return None
    validate_keys(value, keys, keys, f"{location}.", contract_findings)
    validation_id = value.get("validation_id")
    if not isinstance(validation_id, str) or re.fullmatch(r"AV-[A-Za-z0-9][A-Za-z0-9._-]*", validation_id) is None:
        add_error(contract_findings, "scientific-achieved-validation-id", f"{location}.validation_id", "Invalid AV-* identifier.")
    dimensions = validate_dimensions(value.get("dimensions"), f"{location}.dimensions", contract_findings)
    input_ids = validate_id_list(value.get("input_source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.input_source_ids", contract_findings, allow_empty=False)
    evaluation_ids = validate_id_list(value.get("evaluation_source_ids"), r"SRC-[0-9A-F]{16}", f"{location}.evaluation_source_ids", contract_findings, allow_empty=False)
    if not set(input_ids) <= set(spec.get("input_source_ids", [])):
        add_error(contract_findings, "scientific-validation-source-scope", f"{location}.input_source_ids", "Validation inputs are outside the analysis source set.")
    if not set(evaluation_ids) <= set(input_ids):
        add_error(contract_findings, "scientific-validation-evaluation-scope", f"{location}.evaluation_source_ids", "Evaluation sources must be a subset of validation inputs.")
    relation = dimensions.get("data_relation")
    if relation == "same_observations" and not set(evaluation_ids) <= set(spec.get("primary_source_ids", [])):
        add_error(contract_findings, "scientific-validation-source-relation", f"{location}.evaluation_source_ids", "same_observations must evaluate primary sources.")
    if relation in {"independent_sampling_frame", "same_subjects_new_measurement"} and not set(evaluation_ids) <= set(spec.get("independent_source_ids", [])):
        add_error(contract_findings, "scientific-validation-source-relation", f"{location}.evaluation_source_ids", "This data relation requires independent-validation sources.")
    evaluation_artifact_ids = validate_id_list(value.get("evaluation_input_artifact_ids"), r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", f"{location}.evaluation_input_artifact_ids", contract_findings, allow_empty=False)
    gate_ids = validate_string_list(value.get("evidence_gate_ids"), f"{location}.evidence_gate_ids", contract_findings, allow_empty=False)
    evidence_kinds: set[str] = set()
    evidence_run_ids: set[str] = set()
    evidence_artifact_ids: set[str] = set()
    for gate_id in gate_ids:
        gate = gate_map.get(gate_id)
        if gate is None:
            add_error(contract_findings, "scientific-validation-gate-missing", f"{location}.evidence_gate_ids", f"Unknown gate ID {gate_id}.")
            continue
        if gate.get("status") != "PASS":
            add_error(contract_findings, "scientific-validation-gate-status", f"{location}.evidence_gate_ids", f"Validation gate {gate_id} is not PASS.")
        for evidence in gate.get("evidence", []):
            if isinstance(evidence, dict) and isinstance(evidence.get("kind"), str):
                evidence_kinds.add(evidence["kind"])
                if evidence["kind"] == "run" and isinstance(evidence.get("ref"), str):
                    evidence_run_ids.add(evidence["ref"])
                if evidence["kind"] == "artifact" and isinstance(evidence.get("ref"), str):
                    evidence_artifact_ids.add(evidence["ref"])
    resolved_runs = [run_info[run_id] for run_id in evidence_run_ids if run_id in run_info]
    observed_run_sources = set().union(*(item["input_source_ids"] for item in resolved_runs)) if resolved_runs else set()
    if observed_run_sources != set(input_ids):
        add_error(contract_findings, "scientific-validation-run-sources", location, "Validation evidence-run input sources do not exactly match the validation record.")
    run_input_artifacts = set().union(*(item["input_ids"] for item in resolved_runs)) if resolved_runs else set()
    if not set(evaluation_artifact_ids) <= run_input_artifacts:
        add_error(contract_findings, "scientific-validation-input-artifacts", f"{location}.evaluation_input_artifact_ids", "Evaluation artifacts must be inputs of the validation evidence runs.")
    observed_evaluation_sources: set[str] = set()
    for artifact_id in evaluation_artifact_ids:
        row = artifact_rows.get(artifact_id)
        if row is None:
            add_error(contract_findings, "scientific-validation-artifact-missing", f"{location}.evaluation_input_artifact_ids", f"Unknown artifact {artifact_id}.")
            continue
        observed_evaluation_sources.update(parse_source_ids(row.get("source_ids"), f"artifact.{artifact_id}.source_ids", contract_findings, allow_empty=False))
        purposes = artifact_purposes(row, f"artifact.{artifact_id}.evidence_purposes", contract_findings)
        if "scientific_validation" not in purposes:
            add_error(contract_findings, "scientific-validation-artifact-purpose", artifact_id, "Evaluation input artifact lacks scientific_validation purpose.")
    if observed_evaluation_sources != set(evaluation_ids):
        add_error(contract_findings, "scientific-validation-artifact-sources", f"{location}.evaluation_input_artifact_ids", "Evaluation artifact sources do not exactly match evaluation_source_ids.")
    if not is_concrete_string(value.get("success_criterion")) or not is_concrete_string(value.get("observed_result")):
        add_error(contract_findings, "scientific-validation-result", location, "Validation requires a concrete criterion and observed result.")
    validate_enum(value.get("outcome"), {"passed", "failed", "inconclusive"}, f"{location}.outcome", contract_findings, "scientific-validation-outcome")
    validate_binding_shape(value.get("partition_binding"), f"{location}.partition_binding", contract_findings, nullable=True)
    if value.get("partition_binding") is not None:
        validate_binding(root, value["partition_binding"], f"{location}.partition_binding", contract_findings, currency_findings)
    if relation == "held_out_observations":
        if value.get("partition_binding") is None:
            add_error(contract_findings, "scientific-validation-partition", f"{location}.partition_binding", "Held-out validation requires a bound partition.")
        if value.get("partition_unit") != spec.get("document", {}).get("design", {}).get("independent_unit"):
            add_error(contract_findings, "scientific-validation-partition-unit", f"{location}.partition_unit", "Held-out partition must use the independent unit.")
    elif value.get("partition_unit") is not None and not is_concrete_string(value.get("partition_unit")):
        add_error(contract_findings, "scientific-validation-partition-unit", f"{location}.partition_unit", "Expected a concrete string or null.")
    needs_overlap_check = relation in {"held_out_observations", "independent_sampling_frame"}
    validate_binding_shape(value.get("unit_overlap_check"), f"{location}.unit_overlap_check", contract_findings, nullable=True)
    if needs_overlap_check and value.get("unit_overlap_check") is None:
        add_error(contract_findings, "scientific-validation-overlap-check", f"{location}.unit_overlap_check", "Held-out or independent validation requires a zero-overlap check.")
    elif needs_overlap_check:
        validate_overlap_check(root, value.get("unit_overlap_check"), value, spec, assessed_at, contract_findings, currency_findings)
    validate_binding_shape(value.get("timing_check"), f"{location}.timing_check", contract_findings, nullable=True)
    if dimensions.get("collection_timing") == "collected_after_claim_lock":
        if value.get("timing_check") is None:
            add_error(contract_findings, "scientific-validation-timing-check", f"{location}.timing_check", "Prospective collection requires a lock-versus-collection timing check.")
        else:
            validate_timing_check(root, value.get("timing_check"), value, spec, assessed_at, contract_findings, currency_findings)
    planned_id = value.get("planned_validation_id")
    planned = spec.get("planned_map", {}).get(planned_id) if isinstance(planned_id, str) else None
    if isinstance(planned_id, str) and planned is None:
        add_error(contract_findings, "scientific-validation-plan-missing", f"{location}.planned_validation_id", "Planned validation ID is absent from the analysis spec.")
    if planned is not None:
        comparisons = {
            "dimensions": value.get("dimensions"),
            "input_source_ids": value.get("input_source_ids"),
            "evaluation_source_ids": value.get("evaluation_source_ids"),
            "partition_binding": value.get("partition_binding"),
            "partition_unit": value.get("partition_unit"),
            "success_criterion": value.get("success_criterion"),
        }
        for key, observed in comparisons.items():
            if observed != planned.get(key):
                add_error(contract_findings, "scientific-validation-plan-drift", f"{location}.{key}", "Achieved validation differs from its locked plan.")
        if not set(planned.get("planned_evidence_kinds", [])) <= evidence_kinds:
            add_error(contract_findings, "scientific-validation-planned-evidence", f"{location}.evidence_gate_ids", "Evidence lacks one or more kinds required by the validation plan.")
    plan_lock_time = spec.get("plan_lock_time")
    run_start_times = [
        item.get("started_at") for item in resolved_runs if item.get("started_at")
    ]
    plan_locked_before_runs = bool(
        planned is not None
        and plan_lock_time is not None
        and run_start_times
        and all(plan_lock_time <= started_at for started_at in run_start_times)
    )
    if planned is not None and not plan_locked_before_runs:
        add_error(
            contract_findings,
            "scientific-validation-plan-not-locked",
            f"{location}.planned_validation_id",
            "A planned validation requires a bound protocol lock at or before every evidence-run start.",
        )
    return {
        **value,
        "resolved_dimensions": dimensions,
        "resolved_evidence_kinds": evidence_kinds,
        "resolved_run_ids": evidence_run_ids,
        "resolved_artifact_ids": evidence_artifact_ids,
        "is_planned": plan_locked_before_runs,
    }


def validation_matches_requirement(
    validation: dict[str, Any], requirement: dict[str, Any], *, planned: bool
) -> bool:
    profile = validation.get("dimensions", {})
    constraints = requirement.get("dimension_constraints", {})
    if not isinstance(profile, dict) or not isinstance(constraints, dict):
        return False
    if any(profile.get(dimension) not in accepted for dimension, accepted in constraints.items() if isinstance(accepted, list)):
        return False
    evidence_kinds = set(validation.get("planned_evidence_kinds", [])) if planned else set(validation.get("resolved_evidence_kinds", []))
    if not set(requirement.get("required_evidence_kinds", [])) <= evidence_kinds:
        return False
    if requirement.get("must_be_planned") is True:
        planned_status = (
            validation.get("_is_locked_plan")
            if planned
            else validation.get("is_planned")
        )
        if planned_status is not True:
            return False
    if not planned and validation.get("outcome") != "passed":
        return False
    return True


def validate_source_manifests(
    root: Path,
    bindings: Any,
    input_source_ids: list[str],
    source_status: Any,
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> tuple[list[str], str, str, dict[str, dict[str, Any]]]:
    statuses: list[str] = []
    manifest_contract = "not_assessed"
    integrity = "not_assessed"
    source_records: dict[str, dict[str, Any]] = {}
    if not isinstance(bindings, list):
        add_error(contract_findings, "scientific-input-manifests", "input_manifests", "Expected a list of manifest bindings.")
        return statuses, manifest_contract, integrity, source_records
    if source_status == "not_applicable":
        if bindings or input_source_ids:
            add_error(contract_findings, "scientific-source-not-applicable", "input_manifests", "not_applicable provenance requires no manifests or source IDs.")
        return statuses, manifest_contract, integrity, source_records
    if not bindings:
        add_error(contract_findings, "scientific-input-manifests", "input_manifests", "Data-bearing readiness requires at least one source manifest.")
        return statuses, manifest_contract, integrity, source_records
    binding_signatures: set[str] = set()
    reports: list[dict[str, Any]] = []
    for index, binding in enumerate(bindings):
        location = f"input_manifests[{index}]"
        signature = json.dumps(binding, ensure_ascii=False, sort_keys=True, allow_nan=False) if isinstance(binding, dict) else repr(binding)
        if signature in binding_signatures:
            add_error(contract_findings, "scientific-input-manifest-duplicate", location, "Duplicate source-manifest binding.")
        binding_signatures.add(signature)
        status, path = validate_binding(root, binding, location, contract_findings, currency_findings)
        statuses.append(status)
        if status != "current" or path is None:
            continue
        try:
            manifest = load_json_object(path)
            report = verify_source_manifest_document(root, manifest)
        except ContractError as exc:
            add_error(contract_findings, "scientific-input-manifest-read", location, str(exc))
            continue
        reports.append(report)
        if report["manifest_contract_status"] == "invalid":
            contract_findings.extend(report["findings"])
        else:
            currency_findings.extend(report["findings"])
        try:
            generated_at = parse_rfc3339(manifest.get("generated_at"))
        except ContractError:
            generated_at = None
        if generated_at and assessed_at and generated_at > assessed_at + timedelta(minutes=5):
            add_error(contract_findings, "scientific-source-manifest-after-assessment", location, "Source manifest postdates the assessment.")
        if source_status == "verified":
            gaps = source_provenance_gaps(manifest)
            if gaps:
                add_error(contract_findings, "scientific-source-provenance-incomplete", f"{location}.source_context", f"Verified provenance lacks identity context: {gaps}.")
        context = manifest.get("source_context") if isinstance(manifest.get("source_context"), dict) else {}
        for entry in manifest.get("entries", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("source_id"), str):
                continue
            source_id = entry["source_id"]
            if source_id in source_records:
                add_error(contract_findings, "scientific-source-id-ambiguous", location, f"Source ID {source_id} occurs in more than one manifest.")
            else:
                source_records[source_id] = {"entry": entry, "context": context, "manifest": binding}
    missing_ids = sorted(set(input_source_ids) - set(source_records))
    extra_ids = sorted(set(source_records) - set(input_source_ids))
    if missing_ids:
        add_error(contract_findings, "scientific-source-id-missing", "input_source_ids", f"Source IDs are absent from all bound manifests: {missing_ids}.")
    if extra_ids:
        contract_findings.append(finding("info", "scientific-source-manifest-extra", "input_manifests", f"Bound manifests include unused source IDs: {extra_ids}."))
    if reports:
        manifest_contract = "invalid" if any(item["manifest_contract_status"] == "invalid" for item in reports) else "valid"
        integrity_values = {item["source_integrity_status"] for item in reports}
        integrity = "fail" if "fail" in integrity_values else "review" if "review" in integrity_values else "pass"
    return statuses, manifest_contract, integrity, source_records


def validate_unit_map(
    root: Path,
    binding: Any,
    expected_count: Any,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> str:
    status, path = validate_binding(root, binding, "analysis_spec.design.unit_map", contract_findings, currency_findings)
    if status != "current" or path is None:
        return status
    required_columns = {"observation_id", "independent_unit_id", "analysis_set_included"}
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None or not required_columns <= set(reader.fieldnames):
                raise ContractError(f"Unit map requires columns {sorted(required_columns)}")
            rows = list(reader)
            if not rows or any(None in row for row in rows):
                raise ContractError("Unit map must contain well-formed rows")
    except (OSError, UnicodeError, csv.Error, ContractError) as exc:
        add_error(contract_findings, "analysis-spec-unit-map", "analysis_spec.design.unit_map", str(exc))
        return "invalid"
    observation_ids = [row.get("observation_id", "") for row in rows]
    if any(not value for value in observation_ids) or len(observation_ids) != len(set(observation_ids)):
        add_error(contract_findings, "analysis-spec-unit-map-observations", "analysis_spec.design.unit_map", "Observation IDs must be non-empty and unique.")
    if any(row.get("analysis_set_included") not in {"true", "false"} for row in rows):
        add_error(contract_findings, "analysis-spec-unit-map-inclusion", "analysis_spec.design.unit_map", "analysis_set_included must be true or false.")
    included = [row for row in rows if row.get("analysis_set_included") == "true"]
    independent_ids = {row.get("independent_unit_id") for row in included if row.get("independent_unit_id")}
    if not included or any(not row.get("independent_unit_id") for row in included):
        add_error(contract_findings, "analysis-spec-unit-map-independent-unit", "analysis_spec.design.unit_map", "Included observations require independent-unit IDs.")
    if type(expected_count) is int and len(independent_ids) != expected_count:
        add_error(contract_findings, "analysis-spec-unit-count-mismatch", "analysis_spec.design.n_independent_units", f"Declared {expected_count} independent units but the bound unit map contains {len(independent_ids)} included units.")
    return status


def validate_spec_bindings(
    root: Path,
    spec: dict[str, Any],
    assessed_at: datetime | None,
    contract_findings: list[dict[str, str]],
    currency_findings: list[dict[str, str]],
) -> list[str]:
    document = spec["document"]
    statuses: list[str] = []
    if spec.get("created_at") and assessed_at and spec["created_at"] > assessed_at + timedelta(minutes=5):
        add_error(contract_findings, "analysis-spec-after-assessment", "analysis_spec.created_at", "Analysis spec postdates the assessment.")
    if assessed_at:
        for key, timestamp in spec.get("prespec_times", {}).items():
            if timestamp and timestamp > assessed_at + timedelta(minutes=5):
                add_error(
                    contract_findings,
                    "analysis-spec-prespecification-after-assessment",
                    f"analysis_spec.prespecification.{key}",
                    "Prespecification timing cannot postdate the readiness assessment.",
                )
    design = document.get("design") if isinstance(document.get("design"), dict) else {}
    if document.get("data_requirement") == "data_bearing":
        statuses.append(validate_unit_map(root, design.get("unit_map"), design.get("n_independent_units"), contract_findings, currency_findings))
        for key in ("analysis_set_manifest",):
            status, path = validate_binding(root, design.get(key), f"analysis_spec.design.{key}", contract_findings, currency_findings)
            statuses.append(status)
            if status == "current" and path is not None:
                try:
                    if path.stat().st_size == 0:
                        add_error(contract_findings, "analysis-spec-empty-binding", f"analysis_spec.design.{key}", "Bound analysis-set manifest must not be empty.")
                except OSError as exc:
                    add_error(currency_findings, "analysis-spec-binding-unverifiable", f"analysis_spec.design.{key}", str(exc))
    for location, binding in (
        ("analysis_spec.domain_spec", document.get("domain_spec")),
        ("analysis_spec.design.deviation_log", design.get("deviation_log")),
    ):
        if binding is not None:
            status, _ = validate_binding(root, binding, location, contract_findings, currency_findings)
            statuses.append(status)
    prespec = document.get("prespecification") if isinstance(document.get("prespecification"), dict) else {}
    if prespec.get("protocol") is not None:
        status, _ = validate_binding(root, prespec["protocol"], "analysis_spec.prespecification.protocol", contract_findings, currency_findings)
        statuses.append(status)
    for validation_id, validation in spec.get("planned_map", {}).items():
        if validation.get("partition_binding") is not None:
            status, _ = validate_binding(root, validation["partition_binding"], f"analysis_spec.planned_validations.{validation_id}.partition_binding", contract_findings, currency_findings)
            statuses.append(status)
    return statuses


def validate_document_v2(
    root: Path,
    document: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_days: int | None = None,
    current_code_revision: str | None = None,
    current_code_dirty: bool | None = None,
    current_backend_revision: str | None = None,
) -> dict[str, Any]:
    contract_findings: list[dict[str, str]] = []
    policy_findings: list[dict[str, str]] = []
    currency_findings: list[dict[str, str]] = []
    report_keys = {
        "schema_version",
        "readiness_id",
        "analysis_id",
        "scope_id",
        "readiness_purpose",
        "intended_use",
        "claim",
        "source_roles",
        "policy_authorization_id",
        "assessor",
        "assessed_at",
        "source_provenance_status",
        "readiness_status",
        "claim_authorization",
        "lifecycle_status",
        "gate_policy",
        "analysis_spec",
        "input_manifests",
        "input_source_ids",
        "code_manifest",
        "environment_manifest",
        "code_revision",
        "code_dirty",
        "backend_revision",
        "dependencies",
        "claim_support_gate_id",
        "curation_artifact_ids",
        "achieved_validations",
        "claim_boundary_notes",
        "gates",
    }
    required_report_keys = report_keys - {"dependencies"}
    validate_keys(document, report_keys, required_report_keys, "", contract_findings)
    if document.get("schema_version") != READINESS_SCHEMA:
        add_error(contract_findings, "scientific-readiness-schema", "schema_version", f"Expected {READINESS_SCHEMA}.")
    for key in ("readiness_id", "analysis_id", "scope_id", "intended_use", "code_revision"):
        if not is_concrete_string(document.get(key)):
            add_error(contract_findings, "scientific-readiness-field", key, "Expected a concrete string.")
    validate_enum(document.get("readiness_purpose"), PURPOSES, "readiness_purpose", contract_findings, "scientific-readiness-purpose")
    validate_enum(document.get("source_provenance_status"), SOURCE_STATES, "source_provenance_status", contract_findings, "scientific-source-status")
    validate_enum(document.get("readiness_status"), READINESS_STATES, "readiness_status", contract_findings, "scientific-readiness-status")
    validate_enum(document.get("claim_authorization"), {"authorized", "not_authorized"}, "claim_authorization", contract_findings, "scientific-claim-authorization")
    validate_enum(document.get("lifecycle_status"), LIFECYCLE_STATES, "lifecycle_status", contract_findings, "scientific-lifecycle")
    claim = validate_claim(document.get("claim"), "claim", contract_findings)
    report_primary_ids, report_independent_ids = validate_source_roles(document.get("source_roles"), "source_roles", contract_findings)
    input_source_ids = validate_id_list(document.get("input_source_ids"), r"SRC-[0-9A-F]{16}", "input_source_ids", contract_findings, allow_empty=document.get("source_provenance_status") == "not_applicable")
    if set(input_source_ids) != set(report_primary_ids) | set(report_independent_ids):
        add_error(contract_findings, "scientific-source-role-closure", "input_source_ids", "Report source IDs must exactly equal the source-role union.")
    if claim is not None and not set(claim.get("source_ids", [])) <= set(input_source_ids):
        add_error(contract_findings, "scientific-claim-source-scope", "claim.source_ids", "Claim source IDs must be a subset of report inputs.")
    assessor = document.get("assessor")
    if not isinstance(assessor, dict):
        add_error(contract_findings, "scientific-assessor", "assessor", "Expected a name/version object.")
    else:
        validate_keys(assessor, {"name", "version"}, {"name", "version"}, "assessor.", contract_findings)
        for key in ("name", "version"):
            if not is_concrete_string(assessor.get(key)):
                add_error(contract_findings, "scientific-assessor", f"assessor.{key}", "Expected a concrete string.")
    assessed_at: datetime | None = None
    check_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        assessed_at = parse_rfc3339(document.get("assessed_at"))
    except ContractError as exc:
        add_error(contract_findings, "scientific-assessed-at", "assessed_at", str(exc))
    if assessed_at and assessed_at > check_time + timedelta(minutes=5):
        add_error(contract_findings, "scientific-assessment-future", "assessed_at", "Assessment time is in the future.")
    if assessed_at and max_age_days is not None and check_time - assessed_at > timedelta(days=max_age_days):
        add_error(currency_findings, "scientific-assessment-expired", "assessed_at", "Assessment exceeds the requested maximum age.")
    if type(document.get("code_dirty")) is not bool:
        add_error(contract_findings, "scientific-code-dirty", "code_dirty", "Expected a boolean.")
    backend_revision = document.get("backend_revision")
    if backend_revision is not None and not is_concrete_string(backend_revision):
        add_error(contract_findings, "scientific-backend-revision", "backend_revision", "Expected a concrete string or null.")
    validate_string_list(document.get("claim_boundary_notes"), "claim_boundary_notes", contract_findings, allow_empty=True)

    binding_status: dict[str, str] = {}
    binding_paths: dict[str, Path | None] = {}
    for label in ("gate_policy", "analysis_spec", "code_manifest", "environment_manifest"):
        status, path = validate_binding(root, document.get(label), label, contract_findings, currency_findings)
        binding_status[label] = status
        binding_paths[label] = path
    dependency_statuses: list[str] = []
    dependencies = document.get("dependencies", [])
    if not isinstance(dependencies, list):
        add_error(contract_findings, "scientific-dependencies", "dependencies", "Expected a list of file bindings.")
    else:
        for index, dependency in enumerate(dependencies):
            status, _ = validate_binding(root, dependency, f"dependencies[{index}]", contract_findings, currency_findings)
            dependency_statuses.append(status)

    policy: dict[str, Any] | None = None
    policy_contract_valid = False
    policy_path = binding_paths.get("gate_policy")
    if binding_status.get("gate_policy") == "current" and policy_path is not None:
        try:
            policy_document = load_json_object(policy_path)
            policy, findings = validate_policy_document_v2(policy_document)
            policy_contract_valid = not any(
                item["level"] == "error" for item in findings
            )
            contract_findings.extend(findings)
        except ContractError as exc:
            add_error(contract_findings, "scientific-policy-read", "gate_policy", str(exc))
    spec: dict[str, Any] | None = None
    spec_path = binding_paths.get("analysis_spec")
    if binding_status.get("analysis_spec") == "current" and spec_path is not None:
        try:
            spec_document = load_json_object(spec_path)
            spec, findings = validate_spec_document(spec_document)
            contract_findings.extend(findings)
        except ContractError as exc:
            add_error(contract_findings, "scientific-spec-read", "analysis_spec", str(exc))
    if spec is not None:
        spec_document = spec["document"]
        for key in ("analysis_id", "scope_id", "readiness_purpose", "intended_use", "backend_revision"):
            if document.get(key) != spec_document.get(key):
                add_error(contract_findings, "scientific-spec-report-mismatch", key, f"Report {key} does not match the bound spec.")
        if document.get("claim") != spec_document.get("claim"):
            add_error(contract_findings, "scientific-exact-claim-mismatch", "claim", "Report claim must exactly match the claim locked in the analysis spec.")
        if document.get("source_roles") != spec_document.get("source_roles"):
            add_error(contract_findings, "scientific-source-role-mismatch", "source_roles", "Report source roles do not exactly match the analysis spec.")
        if set(input_source_ids) != set(spec.get("input_source_ids", [])):
            add_error(contract_findings, "scientific-source-id-mismatch", "input_source_ids", "Report source IDs do not match the analysis spec.")
        dependency_statuses.extend(validate_spec_bindings(root, spec, assessed_at, contract_findings, currency_findings))

    source_statuses, manifest_contract_status, source_integrity_status, source_records = validate_source_manifests(
        root,
        document.get("input_manifests"),
        input_source_ids,
        document.get("source_provenance_status"),
        assessed_at,
        contract_findings,
        currency_findings,
    )
    dependency_statuses.extend(source_statuses)
    if spec is not None:
        data_requirement = spec["document"].get("data_requirement")
        if data_requirement == "data_bearing" and document.get("source_provenance_status") == "not_applicable":
            add_error(contract_findings, "scientific-source-status-mismatch", "source_provenance_status", "Data-bearing analysis cannot declare sources not applicable.")
        if data_requirement == "none" and document.get("source_provenance_status") != "not_applicable":
            add_error(contract_findings, "scientific-source-status-mismatch", "source_provenance_status", "Data-free analysis must declare sources not applicable.")

    code_manifest_contract_status = "not_assessed"
    code_integrity_status = "not_assessed"
    code_path = binding_paths.get("code_manifest")
    if binding_status.get("code_manifest") == "current" and code_path is not None:
        try:
            code_manifest = load_json_object(code_path)
            code_report = verify_source_manifest_document(root, code_manifest)
            code_manifest_contract_status = code_report["manifest_contract_status"]
            code_integrity_status = code_report["source_integrity_status"]
            if code_manifest_contract_status == "invalid":
                contract_findings.extend(code_report["findings"])
            else:
                currency_findings.extend(code_report["findings"])
            if spec is not None:
                code_paths = {
                    entry.get("path")
                    for entry in code_manifest.get("entries", [])
                    if isinstance(entry, dict) and entry.get("hash_status") == "recorded"
                }
                missing_entry_points = sorted(set(spec.get("entry_points", [])) - code_paths)
                if missing_entry_points:
                    add_error(contract_findings, "scientific-code-entry-points", "code_manifest.entries", f"Code manifest misses entry points: {missing_entry_points}.")
        except ContractError as exc:
            add_error(contract_findings, "scientific-code-manifest-read", "code_manifest", str(exc))

    environment_id: str | None = None
    environment_working_directory: str | None = None
    environment_path = binding_paths.get("environment_manifest")
    if binding_status.get("environment_manifest") == "current" and environment_path is not None:
        try:
            environment_document = load_json_object(environment_path)
            environment_id, environment_working_directory, environment_statuses = validate_environment_document(
                root,
                environment_document,
                assessed_at,
                contract_findings,
                currency_findings,
            )
            dependency_statuses.extend(environment_statuses)
        except ContractError as exc:
            add_error(contract_findings, "scientific-environment-read", "environment_manifest", str(exc))

    revision_statuses: list[str] = []
    for value, current, path, code in (
        (document.get("code_revision"), current_code_revision, "code_revision", "scientific-code-revision"),
        (document.get("code_dirty"), current_code_dirty, "code_dirty", "scientific-code-dirty"),
        (document.get("backend_revision"), current_backend_revision, "backend_revision", "scientific-backend-revision"),
    ):
        if value is None and path == "backend_revision":
            continue
        if current is None:
            currency_findings.append(finding("warning", f"{code}-unchecked", path, "Current value was not supplied; currency is unknown."))
            revision_statuses.append("unknown")
        elif value != current:
            add_error(currency_findings, f"{code}-stale", path, "Recorded value differs from the supplied current value.")
            revision_statuses.append("stale")

    gates_value = document.get("gates")
    if not isinstance(gates_value, list) or not gates_value:
        add_error(contract_findings, "scientific-gates", "gates", "Expected at least one gate.")
        gates_value = []
    report_gate_map: dict[str, dict[str, Any]] = {}
    mandatory_problem = bool(spec and spec.get("design_blocker")) or document.get("source_provenance_status") in {"unverified", "conflicting"}
    advisory_problem = False
    gate_keys = {
        "gate_id",
        "gate_category",
        "required_for_ready",
        "status",
        "requirement",
        "evidence",
        "impact",
        "remediation",
    }
    for index, gate in enumerate(gates_value):
        location = f"gates[{index}]"
        if not isinstance(gate, dict):
            add_error(contract_findings, "scientific-gate", location, "Expected an object.")
            continue
        validate_keys(gate, gate_keys, gate_keys, f"{location}.", contract_findings)
        gate_id = gate.get("gate_id")
        if not is_concrete_string(gate_id):
            add_error(contract_findings, "scientific-gate-id", f"{location}.gate_id", "Expected a concrete gate ID.")
        elif gate_id in report_gate_map:
            add_error(contract_findings, "scientific-gate-duplicate", f"{location}.gate_id", "Duplicate gate ID.")
        validate_enum(gate.get("gate_category"), GATE_CATEGORIES, f"{location}.gate_category", contract_findings, "scientific-gate-category")
        if type(gate.get("required_for_ready")) is not bool:
            add_error(contract_findings, "scientific-gate-required", f"{location}.required_for_ready", "Expected a boolean.")
        validate_enum(gate.get("status"), GATE_STATES, f"{location}.status", contract_findings, "scientific-gate-status")
        if not is_concrete_string(gate.get("requirement")):
            add_error(contract_findings, "scientific-gate-requirement", f"{location}.requirement", "Expected a concrete requirement.")
        if not isinstance(gate.get("impact"), str) or not isinstance(gate.get("remediation"), str):
            add_error(contract_findings, "scientific-gate-text", location, "Impact and remediation must be strings.")
        if gate.get("status") in {"FAIL", "UNKNOWN"} and not is_concrete_string(gate.get("remediation")):
            add_error(contract_findings, "scientific-gate-remediation", f"{location}.remediation", "FAIL/UNKNOWN requires remediation.")
        raw_evidence = gate.get("evidence")
        projected_evidence: Any = raw_evidence
        if isinstance(raw_evidence, list):
            projected_evidence = []
            for item in raw_evidence:
                if isinstance(item, dict) and item.get("kind") == "run":
                    projected = dict(item)
                    projected.pop("lineage_record_sha256s", None)
                    projected_evidence.append(projected)
                else:
                    projected_evidence.append(item)
        validated_evidence = validate_evidence_list(
            root,
            projected_evidence,
            f"{location}.evidence",
            contract_findings,
            currency_findings,
            allow_empty=gate.get("status") not in {"PASS", "NA"},
            gate_status=gate.get("status"),
            analysis_id=document.get("analysis_id"),
            scope_id=document.get("scope_id"),
            assessed_at=assessed_at,
            analysis_spec_binding=document.get("analysis_spec"),
            environment_snapshot_binding=document.get("environment_manifest"),
            code_revision=document.get("code_revision"),
            code_dirty=document.get("code_dirty"),
            backend_revision=document.get("backend_revision"),
            entry_points=spec.get("entry_points", []) if spec else [],
            data_requirement=spec.get("document", {}).get("data_requirement") if spec else None,
            input_source_ids=input_source_ids,
        )
        if gate.get("status") in {"PASS", "NA"} and not validated_evidence:
            add_error(contract_findings, "scientific-gate-evidence", f"{location}.evidence", "PASS/NA requires typed evidence.")
        if isinstance(gate_id, str) and gate_id not in report_gate_map:
            report_gate_map[gate_id] = {**gate, "evidence": raw_evidence if isinstance(raw_evidence, list) else []}
        if gate.get("status") in {"FAIL", "UNKNOWN"}:
            if gate.get("required_for_ready") is True:
                mandatory_problem = True
            elif gate.get("required_for_ready") is False:
                advisory_problem = True

    policy_status = "not_assessed"
    selected_authorization: dict[str, Any] | None = None
    required_categories: set[str] = set()
    if policy is not None:
        policy_status = "conformant" if policy_contract_valid else "nonconformant"
        policy_document = policy["document"]
        if spec is not None:
            spec_document = spec["document"]
            applicability_checks = (
                (spec_document.get("domain") == policy_document.get("domain"), "policy-domain", "Policy domain does not match the spec."),
                (spec_document.get("study_type") in policy_document.get("applicable_study_types", []), "policy-study-type", "Study type is outside policy applicability."),
                (spec_document.get("data_requirement") in policy_document.get("applicable_data_requirements", []), "policy-data-requirement", "Data requirement is outside policy applicability."),
                (document.get("readiness_purpose") in policy_document.get("applicable_readiness_purposes", []), "policy-purpose", "Readiness purpose is outside policy applicability."),
            )
            for valid, code, message in applicability_checks:
                if not valid:
                    add_error(policy_findings, code, "gate_policy", message)
                    policy_status = "nonconformant"
        policy_assessor = policy_document.get("assessor") if isinstance(policy_document.get("assessor"), dict) else {}
        if not isinstance(assessor, dict) or assessor != policy_assessor:
            add_error(policy_findings, "policy-assessor-mismatch", "assessor", "Report assessor name/version must exactly match policy.")
            policy_status = "nonconformant"
        authorization_id = document.get("policy_authorization_id")
        selected_authorization = policy.get("authorization_map", {}).get(authorization_id)
        if selected_authorization is None:
            add_error(policy_findings, "policy-authorization-missing", "policy_authorization_id", "Selected authorization ID is absent from the policy.")
            policy_status = "nonconformant"
        elif spec is not None and claim is not None:
            expected_tuple = (
                document.get("readiness_purpose"),
                spec["document"].get("analysis_mode"),
                claim.get("claim_class"),
            )
            observed_tuple = (
                selected_authorization.get("readiness_purpose"),
                selected_authorization.get("analysis_mode"),
                selected_authorization.get("claim_class"),
            )
            if expected_tuple != observed_tuple:
                add_error(policy_findings, "policy-authorization-mismatch", "policy_authorization_id", "Selected authorization does not match purpose/mode/claim class.")
                policy_status = "nonconformant"
        policy_gates = policy.get("gate_map", {})
        missing_gate_ids = sorted(set(policy_gates) - set(report_gate_map))
        extra_gate_ids = sorted(set(report_gate_map) - set(policy_gates))
        if missing_gate_ids or extra_gate_ids:
            add_error(policy_findings, "policy-gate-set", "gates", f"Gate set differs from policy; missing={missing_gate_ids}, extra={extra_gate_ids}.")
            policy_status = "nonconformant"
        for gate_id in sorted(set(policy_gates) & set(report_gate_map)):
            policy_gate = policy_gates[gate_id]
            report_gate = report_gate_map[gate_id]
            for key in ("gate_category", "required_for_ready", "requirement"):
                if report_gate.get(key) != policy_gate.get(key):
                    add_error(policy_findings, "policy-gate-mismatch", f"gates.{gate_id}.{key}", "Report gate differs from policy.")
                    policy_status = "nonconformant"
            if report_gate.get("status") == "NA" and policy_gate.get("allow_na") is not True:
                add_error(policy_findings, "policy-gate-na", f"gates.{gate_id}.status", "Policy does not allow NA.")
                policy_status = "nonconformant"
            if report_gate.get("status") in {"PASS", "NA"}:
                actual_kinds = {
                    item.get("kind")
                    for item in report_gate.get("evidence", [])
                    if isinstance(item, dict) and isinstance(item.get("kind"), str)
                }
                missing_kinds = sorted(set(policy_gate.get("required_evidence_kinds", [])) - actual_kinds)
                if missing_kinds:
                    add_error(policy_findings, "policy-gate-evidence-kinds", f"gates.{gate_id}.evidence", f"Gate lacks policy-required evidence kinds: {missing_kinds}.")
                    policy_status = "nonconformant"
        minima = selected_authorization.get("minimum_validation_requirements", []) if selected_authorization else []
        data_requirement = spec.get("document", {}).get("data_requirement") if spec else None
        mode = spec.get("document", {}).get("analysis_mode") if spec else None
        claim_class = claim.get("claim_class") if claim else None
        required_categories = required_gate_categories(document.get("readiness_purpose"), data_requirement, mode, claim_class, bool(minima))
        covered_categories = {
            gate.get("gate_category")
            for gate in policy_gates.values()
            if gate.get("required_for_ready") is True
        }
        missing_categories = sorted(required_categories - covered_categories)
        if missing_categories:
            add_error(policy_findings, "policy-scientific-gate-floor", "gate_policy.gates", f"Policy omits required scientific gate categories: {missing_categories}.")
            policy_status = "nonconformant"
        na_bypass_categories = sorted(
            category
            for category in required_categories
            if not any(
                gate.get("gate_category") == category
                and gate.get("required_for_ready") is True
                and gate.get("allow_na") is False
                for gate in policy_gates.values()
            )
        )
        if na_bypass_categories:
            add_error(
                policy_findings,
                "policy-scientific-gate-na-bypass",
                "gate_policy.gates",
                "Required scientific categories need at least one mandatory gate "
                f"that cannot be marked NA: {na_bypass_categories}.",
            )
            policy_status = "nonconformant"
        if document.get("readiness_purpose") in NON_EXECUTION_PURPOSES and claim_class != "observation" and not minima:
            add_error(policy_findings, "policy-validation-minimum-missing", "policy_authorization_id", "Post-result authorization of a non-observation claim requires at least one non-ordinal validation minimum.")
            policy_status = "nonconformant"
        if claim_class == "prediction" and minima:
            if not any(set(requirement.get("dimension_constraints", {}).get("data_relation", [])) & {"held_out_observations", "independent_sampling_frame"} for requirement in minima):
                add_error(policy_findings, "policy-prediction-validation-floor", "policy_authorization_id", "Prediction claims require held-out or independent-sampling validation in the policy minimum.")
                policy_status = "nonconformant"
        if claim_class == "clinical_utility" and minima:
            prospective = any(
                "collected_after_claim_lock" in requirement.get("dimension_constraints", {}).get("collection_timing", [])
                and "independent_sampling_frame" in requirement.get("dimension_constraints", {}).get("data_relation", [])
                for requirement in minima
            )
            if not prospective:
                add_error(policy_findings, "policy-clinical-validation-floor", "policy_authorization_id", "Clinical-utility claims require prospectively collected independent-sampling validation.")
                policy_status = "nonconformant"

    artifact_rows = load_artifact_registry(root, contract_findings)
    run_evidence_by_id: dict[str, dict[str, Any]] = {}
    for gate in report_gate_map.values():
        for evidence in gate.get("evidence", []):
            if not isinstance(evidence, dict) or evidence.get("kind") != "run" or not isinstance(evidence.get("ref"), str):
                continue
            run_id = evidence["ref"]
            prior = run_evidence_by_id.get(run_id)
            if prior is not None and prior != evidence:
                add_error(contract_findings, "scientific-run-evidence-conflict", run_id, "The same run ID has conflicting evidence bindings across gates.")
            else:
                run_evidence_by_id[run_id] = evidence
    run_info: dict[str, dict[str, Any]] = {}
    for run_id, evidence in run_evidence_by_id.items():
        resolved = resolve_v2_run(
            root,
            evidence,
            artifact_rows,
            document.get("analysis_id"),
            spec.get("document", {}).get("data_requirement") if spec else None,
            input_source_ids,
            assessed_at,
            environment_id,
            environment_working_directory,
            contract_findings,
            currency_findings,
        )
        if resolved is not None:
            run_info[run_id] = resolved

    achieved_value = document.get("achieved_validations")
    achieved_map: dict[str, dict[str, Any]] = {}
    if not isinstance(achieved_value, list):
        add_error(contract_findings, "scientific-achieved-validations", "achieved_validations", "Expected a list.")
        achieved_value = []
    if document.get("readiness_purpose") == "analysis_execution" and achieved_value:
        add_error(contract_findings, "scientific-execution-achieved-validation", "achieved_validations", "Execution readiness evaluates locked plans, not post-result achieved validations.")
    if spec is not None:
        for index, validation in enumerate(achieved_value):
            resolved = validate_achieved_validation(
                root,
                validation,
                index,
                spec,
                report_gate_map,
                run_info,
                artifact_rows,
                assessed_at,
                contract_findings,
                currency_findings,
            )
            if resolved is None:
                continue
            validation_id = resolved.get("validation_id")
            if isinstance(validation_id, str):
                if validation_id in achieved_map:
                    add_error(contract_findings, "scientific-achieved-validation-duplicate", f"achieved_validations[{index}].validation_id", "Duplicate achieved validation ID.")
                else:
                    achieved_map[validation_id] = resolved

    minima = selected_authorization.get("minimum_validation_requirements", []) if selected_authorization else []
    minimum_coverage: dict[str, list[str]] = {}
    if document.get("readiness_purpose") == "analysis_execution":
        candidates = (
            [
                {
                    **validation,
                    "_is_locked_plan": spec.get("plan_lock_time") is not None,
                }
                for validation in spec.get("planned_map", {}).values()
            ]
            if spec
            else []
        )
        planned_matching = True
    else:
        candidates = list(achieved_map.values())
        planned_matching = False
    for requirement in minima if isinstance(minima, list) else []:
        if not isinstance(requirement, dict) or not isinstance(requirement.get("requirement_id"), str):
            continue
        matches = [
            candidate.get("validation_id")
            for candidate in candidates
            if isinstance(candidate, dict)
            and validation_matches_requirement(candidate, requirement, planned=planned_matching)
            and isinstance(candidate.get("validation_id"), str)
        ]
        minimum_coverage[requirement["requirement_id"]] = matches
        if not matches:
            add_error(policy_findings, "policy-validation-minimum-unmet", "achieved_validations" if not planned_matching else "analysis_spec.planned_validations", f"No validation satisfies minimum requirement {requirement['requirement_id']}.")
            policy_status = "nonconformant"
            mandatory_problem = True
    minimum_status = "met" if minima and all(minimum_coverage.values()) else "not_required" if not minima else "unmet"
    passed_planned_ids = {
        item.get("planned_validation_id")
        for item in achieved_map.values()
        if item.get("outcome") == "passed" and isinstance(item.get("planned_validation_id"), str)
    }
    planned_ids = set(spec.get("planned_map", {})) if spec else set()
    planned_target_status = (
        "planned"
        if document.get("readiness_purpose") == "analysis_execution"
        else "met"
        if planned_ids <= passed_planned_ids
        else "partial"
        if planned_ids & passed_planned_ids
        else "not_met"
    )
    if document.get("readiness_purpose") in NON_EXECUTION_PURPOSES and spec is not None:
        used_independent_sources = set().union(
            *(
                set(item.get("evaluation_source_ids", []))
                for item in achieved_map.values()
                if item.get("outcome") == "passed"
                and item.get("dimensions", {}).get("data_relation")
                in {"independent_sampling_frame", "same_subjects_new_measurement"}
            )
        ) if achieved_map else set()
        unused_independent = sorted(set(spec.get("independent_source_ids", [])) - used_independent_sources)
        if unused_independent:
            add_error(contract_findings, "scientific-independent-source-unused", "achieved_validations", f"Independent-validation sources are not used by a passed validation: {unused_independent}.")

    purpose = document.get("readiness_purpose")
    support_gate_id = document.get("claim_support_gate_id")
    support_gate = report_gate_map.get(support_gate_id) if isinstance(support_gate_id, str) else None
    support_evidence_kinds: set[str] = set()
    support_run_ids: set[str] = set()
    support_artifact_ids: set[str] = set()
    curation_ids = validate_id_list(document.get("curation_artifact_ids"), r"ART-[A-Za-z0-9][A-Za-z0-9._-]*", "curation_artifact_ids", contract_findings, allow_empty=purpose != "result_interpretation")
    claim_support_closed = False
    if purpose == "analysis_execution":
        if support_gate_id is not None:
            add_error(contract_findings, "scientific-execution-claim-gate", "claim_support_gate_id", "Execution readiness must not cite a current claim-support gate.")
        if document.get("claim_authorization") != "not_authorized":
            add_error(contract_findings, "scientific-execution-claim-authorization", "claim_authorization", "Execution readiness cannot authorize claim communication.")
        if curation_ids:
            add_error(contract_findings, "scientific-execution-curation", "curation_artifact_ids", "Execution readiness cannot curate post-result artifacts.")
    else:
        if support_gate is None:
            add_error(contract_findings, "scientific-claim-support-gate", "claim_support_gate_id", "Post-result readiness requires an existing claim-support gate.")
        elif support_gate.get("status") != "PASS" or support_gate.get("required_for_ready") is not True:
            add_error(contract_findings, "scientific-claim-support-gate-status", "claim_support_gate_id", "Claim-support gate must be required and PASS.")
        else:
            for evidence in support_gate.get("evidence", []):
                if not isinstance(evidence, dict) or not isinstance(evidence.get("kind"), str):
                    continue
                support_evidence_kinds.add(evidence["kind"])
                if evidence["kind"] == "run" and isinstance(evidence.get("ref"), str):
                    support_run_ids.add(evidence["ref"])
                if evidence["kind"] == "artifact" and isinstance(evidence.get("ref"), str):
                    support_artifact_ids.add(evidence["ref"])
            required_evidence = set(selected_authorization.get("required_claim_evidence_kinds", [])) if selected_authorization else {"run", "artifact"}
            missing_evidence = sorted(required_evidence - support_evidence_kinds)
            if missing_evidence:
                add_error(policy_findings, "policy-claim-support-evidence", "claim_support_gate_id", f"Claim-support gate lacks authorization-required evidence kinds: {missing_evidence}.")
                policy_status = "nonconformant"
            linked_outputs = set().union(
                *(
                    run_info[run_id]["output_ids"] | run_info[run_id]["validation_ids"]
                    for run_id in support_run_ids
                    if run_id in run_info
                )
            ) if support_run_ids else set()
            unlinked_artifacts = sorted(support_artifact_ids - linked_outputs)
            if unlinked_artifacts:
                add_error(contract_findings, "scientific-claim-artifact-run-link", "claim_support_gate_id", f"Claim-support artifacts are not outputs/validation artifacts of support runs: {unlinked_artifacts}.")
            support_sources: set[str] = set()
            for artifact_id in support_artifact_ids:
                artifact_row = artifact_rows.get(artifact_id)
                if artifact_row is None:
                    continue
                support_sources.update(parse_source_ids(artifact_row.get("source_ids"), f"artifact.{artifact_id}.source_ids", contract_findings, allow_empty=spec is not None and spec.get("document", {}).get("data_requirement") == "none"))
                if "claim_support" not in artifact_purposes(artifact_row, f"artifact.{artifact_id}.evidence_purposes", contract_findings):
                    add_error(contract_findings, "scientific-claim-artifact-purpose", artifact_id, "Claim-support artifact lacks claim_support evidence purpose.")
            expected_claim_sources = set(claim.get("source_ids", [])) if claim else set()
            if support_sources != expected_claim_sources:
                add_error(contract_findings, "scientific-claim-source-evidence", "claim.source_ids", "Claim-support artifact sources do not exactly equal the claim source set.")
            claim_support_closed = not missing_evidence and not unlinked_artifacts and bool(support_run_ids) and bool(support_artifact_ids)
        if purpose == "result_interpretation" and not set(curation_ids) <= support_artifact_ids:
            add_error(contract_findings, "scientific-curation-artifact-scope", "curation_artifact_ids", "Curated artifacts must be directly bound by the claim-support gate.")
        if purpose != "result_interpretation" and curation_ids:
            add_error(contract_findings, "scientific-curation-not-applicable", "curation_artifact_ids", "Curation artifact IDs are reserved for result_interpretation readiness.")
        if purpose == "decision_support" and "decision" not in support_evidence_kinds:
            add_error(contract_findings, "scientific-decision-evidence", "claim_support_gate_id", "Decision support requires decision evidence in the claim-support gate.")

    computed_readiness: str | None = None
    if not any(item["level"] == "error" for item in contract_findings):
        computed_readiness = "blocked" if mandatory_problem else "review" if advisory_problem else "ready"
        if document.get("readiness_status") != computed_readiness:
            add_error(contract_findings, "scientific-readiness-inconsistent", "readiness_status", f"Declared {document.get('readiness_status')}, but evidence gates compute {computed_readiness}.")
    authorization_earned = (
        purpose in NON_EXECUTION_PURPOSES
        and document.get("readiness_status") == "ready"
        and claim_support_closed
        and minimum_status in {"met", "not_required"}
    )
    expected_authorization = "authorized" if authorization_earned else "not_authorized"
    if document.get("claim_authorization") != expected_authorization:
        add_error(policy_findings, "scientific-claim-authorization-unearned", "claim_authorization", f"Expected {expected_authorization} for the current purpose/evidence state.")
        policy_status = "nonconformant"

    if source_integrity_status == "fail" or code_integrity_status == "fail":
        dependency_statuses.append("stale")
    elif source_integrity_status == "review" or code_integrity_status == "review":
        dependency_statuses.append("unknown")
    all_statuses = list(binding_status.values()) + dependency_statuses + revision_statuses
    if "stale" in all_statuses or any(item["level"] == "error" for item in currency_findings):
        currency_status = "stale"
    elif "unknown" in all_statuses or any(item["level"] == "warning" for item in currency_findings):
        currency_status = "unknown"
    else:
        currency_status = "current"
    contract_status = "invalid" if any(item["level"] == "error" for item in contract_findings) else "valid"
    purpose_ready_and_current = (
        contract_status == "valid"
        and currency_status == "current"
        and policy_status == "conformant"
        and document.get("readiness_status") == "ready"
        and document.get("lifecycle_status") == "current"
        and document.get("source_provenance_status") in {"verified", "not_applicable"}
    )
    use_permitted = purpose_ready_and_current and (
        purpose == "analysis_execution" or document.get("claim_authorization") == "authorized"
    )
    findings = contract_findings + policy_findings + currency_findings
    counts = {
        level: sum(item["level"] == level for item in findings)
        for level in ("error", "warning", "info")
    }
    return {
        "contract_status": contract_status,
        "currency_status": currency_status,
        "policy_status": policy_status,
        "manifest_contract_status": manifest_contract_status,
        "source_integrity_status": source_integrity_status,
        "code_manifest_contract_status": code_manifest_contract_status,
        "code_integrity_status": code_integrity_status,
        "readiness_purpose": purpose,
        "claim_id": claim.get("claim_id") if claim else None,
        "declared_readiness": document.get("readiness_status"),
        "computed_readiness": computed_readiness,
        "claim_authorization": document.get("claim_authorization"),
        "minimum_validation_status": minimum_status,
        "minimum_validation_coverage": minimum_coverage,
        "planned_target_status": planned_target_status,
        "required_gate_categories": sorted(required_categories),
        "purpose_ready_and_current": purpose_ready_and_current,
        "use_permitted": use_permitted,
        "claim_release_permitted": use_permitted and purpose == "claim_communication",
        "decision_support_permitted": use_permitted and purpose == "decision_support",
        "scientific_validity": "not_determined_by_contract_validator",
        "counts": counts,
        "findings": findings,
    }
