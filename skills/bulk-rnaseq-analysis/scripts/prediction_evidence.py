"""File-consistency checks for the existing TCGA linear validation contract.

These checks do not certify truthful identities, prediction performance, causal
identification, or clinical usefulness.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from analysis_contract import read_json, sha256_file


def finite_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def read_table(path: Path) -> list[list[str]]:
    if path.suffix.lower() not in {".csv", ".tsv"}:
        raise ValueError("predictive evidence requires inspectable CSV/TSV expression and clinical tables")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ","))
    if len(rows) < 2 or len(rows[0]) < 2 or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError(f"malformed or empty table: {path.name}")
    return rows


def membership(document: object) -> tuple[dict[str, str], str]:
    if not isinstance(document, dict) or document.get("unit") != "patient":
        raise ValueError("membership evidence must declare unit=patient")
    namespace = document.get("unit_namespace")
    if not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("membership evidence needs a common patient-ID namespace")
    rows = document.get("samples")
    if not isinstance(rows, list) or not rows:
        raise ValueError("membership evidence needs sample_id/patient_id rows")
    members = {}
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                            for k in ("sample_id", "patient_id")):
            raise ValueError("invalid membership row")
        if row["sample_id"] in members:
            raise ValueError("duplicate sample ID in membership evidence")
        members[row["sample_id"]] = row["patient_id"]
    return members, namespace


def check_prediction_evidence(spec: dict, spec_dir: Path | None) -> list[str]:
    if spec["experimental_unit"] != "patient" or spec.get("split_policy", {}).get("level") != "patient":
        return ["predictive external validation requires patient experimental and split units"]
    required = {"model_meta_file", "backend_config", "expression_file", "clinical_file",
                "training_units", "validation_units"}
    missing = required - set(spec["inputs"])
    if missing or spec_dir is None:
        return ["actual predictive evidence files are required: " + ", ".join(sorted(missing or required))]
    paths = {key: (spec_dir / spec["inputs"][key]).resolve() for key in required}
    try:
        model, config = read_json(paths["model_meta_file"]), read_json(paths["backend_config"])
        if not isinstance(model, dict) or not isinstance(config, dict):
            raise ValueError("model metadata and backend config must be JSON objects")
        features, coefficients = model.get("features"), model.get("coefficients")
        if (not isinstance(features, list) or len(features) < 2
                or any(not isinstance(x, str) or not x.strip() for x in features)
                or len(set(features)) != len(features)
                or not isinstance(coefficients, dict) or not coefficients
                or not set(coefficients).issubset(features)
                or any(not finite_number(v) for v in coefficients.values())):
            raise ValueError("model requires unique features and finite named coefficients")
        if model.get("method") != "lasso_cox" or model.get("transform") != "log2p1" or not finite_number(model.get("cutoff")):
            raise ValueError("only the existing lasso_cox/log2p1 model with a finite locked cutoff is supported")
        if model.get("covariates") not in (None, []):
            raise ValueError("this backend's external weighted sum cannot reproduce models with clinical covariates")
        if config.get("task") != "external_validate":
            raise ValueError("backend_config must select external_validate")
        for key in ("model_meta_file", "expression_file", "clinical_file"):
            value = config.get(key)
            if not isinstance(value, str) or not Path(value).is_absolute() or Path(value).resolve() != paths[key]:
                raise ValueError(f"backend_config.{key} must be the absolute path of the corresponding hashed input")
        for key in ("weight_file", "signature_file", "feature_genes", "cutoff"):
            if key in config:
                raise ValueError(f"backend_config.{key} may override the locked model; remove this override")
        train_doc, valid_doc = read_json(paths["training_units"]), read_json(paths["validation_units"])
        train, train_namespace = membership(train_doc)
        valid, valid_namespace = membership(valid_doc)
        if train_namespace != valid_namespace:
            raise ValueError("patient namespaces differ; provide reconciled identity/overlap evidence")
        if set(train.values()) & set(valid.values()):
            raise ValueError("training and validation patients overlap")
        if set(train) & set(valid):
            raise ValueError("training and validation sample IDs overlap")
        if len(valid) != len(set(valid.values())):
            raise ValueError("multiple validation samples per patient require a supported patient-level aggregation/model")
        if train_doc.get("model_meta_sha256") != sha256_file(paths["model_meta_file"]):
            raise ValueError("training membership is not bound to the supplied model metadata digest")
        if valid_doc.get("expression_sha256") != sha256_file(paths["expression_file"]) or valid_doc.get("clinical_sha256") != sha256_file(paths["clinical_file"]):
            raise ValueError("validation membership is not bound to expression/clinical digests")
        expression = read_table(paths["expression_file"])
        sample_ids = expression[0][1:]
        if len(set(sample_ids)) != len(sample_ids) or set(sample_ids) != set(valid):
            raise ValueError("expression sample columns do not exactly match validation membership")
        genes = [row[0] for row in expression[1:]]
        if len(set(genes)) != len(genes) or not set(features).issubset(genes):
            raise ValueError("duplicate genes or missing locked model features in validation expression")
        # Even metadata currently leaves a max>100 log-transform heuristic in
        # the backend. This explicit input branch avoids re-deriving a transform.
        if spec["input_scale"] != "log-tpm":
            raise ValueError("this backend's transform heuristic requires explicit log-tpm input for predictive mode; retain preprocessing provenance")
        for row in expression[1:]:
            for value in row[1:]:
                number = float(value)
                if not math.isfinite(number) or number < 0 or number > 100:
                    raise ValueError("log-tpm values must be finite, nonnegative and in the backend's non-transform branch (<=100)")
        clinical = read_table(paths["clinical_file"])
        columns = clinical[0]
        id_name = next((x for x in ("sample_id", "Sample", "sampleID", "barcode", "Patient", "patient_id") if x in columns), None)
        if id_name is None:
            raise ValueError("clinical file lacks a supported sample-ID column")
        clinical_ids = [row[columns.index(id_name)] for row in clinical[1:]]
        if len(set(clinical_ids)) != len(clinical_ids) or set(clinical_ids) != set(valid):
            raise ValueError("clinical sample IDs do not exactly match validation membership")
        time_name = next((x for x in ("OS.time", "os_time", "survival_time", "days_to_event", "time") if x in columns), None)
        event_name = next((x for x in ("OS", "os", "event", "vital_status", "status", "survival_event") if x in columns), None)
        if time_name is None or event_name is None:
            raise ValueError("clinical table needs explicit survival time and event columns")
        for row in clinical[1:]:
            time = float(row[columns.index(time_name)])
            event = float(row[columns.index(event_name)])
            if not math.isfinite(time) or time <= 0 or event not in (0, 1):
                raise ValueError("predictive evidence requires positive finite follow-up and explicit 0/1 event coding")
        if len(valid) < 20:
            raise ValueError("this external-validation backend requires at least 20 complete patients; this is an implementation limit, not a power guarantee")
    except (OSError, ValueError, TypeError) as exc:
        return [str(exc)]
    return []
