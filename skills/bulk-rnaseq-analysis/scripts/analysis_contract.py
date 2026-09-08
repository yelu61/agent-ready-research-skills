"""Shared, dependency-free scale and JSON contracts for routing and preflight."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

INPUT_SCALES = ("raw-counts", "tpm", "log-tpm", "vst", "rlog", "normalized", "other")
# This is a whitelist for the implemented engines, not for every RNA-seq method.
# Estimated counts via tximport are not implemented by these backend routes.
TASK_SCALES = {
    "deg": {"raw-counts"},
    "deseq2": {"raw-counts"},
    "limma-voom": {"raw-counts"},
    "time-course": {"raw-counts"},
    "tme": {"raw-counts", "tpm"},
}


def scale_error(task: str, scale: str) -> str | None:
    allowed = TASK_SCALES.get(task)
    if allowed is None or scale in allowed:
        return None
    return (f"{task} cannot accept {scale}; supported input scales: "
            + ", ".join(sorted(allowed))
            + (". Counts-to-TPM conversion also requires gene lengths." if task == "tme" else "."))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_json(path: Path) -> object:
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def validate_json(value: object, schema: dict, path: str = "$root") -> list[str]:
    """Enforce every validation keyword used by the bundled schema, fail closed
    if a future schema adds an unsupported keyword. No optional library bypass.
    """
    supported = {"$schema", "$id", "title", "description", "type", "required",
                 "properties", "additionalProperties", "enum", "minLength",
                 "minItems", "maxItems", "items", "minProperties"}
    unknown = set(schema) - supported
    if unknown:
        return [f"{path}: unsupported schema keywords: {sorted(unknown)}"]
    types = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "boolean": type(value) is bool,
             "number": type(value) in (int, float) and math.isfinite(value)}
    expected = schema.get("type")
    if expected and not types.get(expected, False):
        return [f"{path}: must be {expected}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(value, str) and len(value.strip()) < schema.get("minLength", 0):
        errors.append(f"{path}: string is too short or blank")
    if isinstance(value, dict):
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: object has too few properties")
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field: {key}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            child = properties.get(key, schema.get("additionalProperties", True))
            if child is False:
                errors.append(f"{path}.{key}: unknown field")
            elif isinstance(child, dict):
                errors.extend(validate_json(item, child, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            errors.append(f"{path}: array length is outside allowed bounds")
        if "items" in schema:
            for i, item in enumerate(value):
                errors.extend(validate_json(item, schema["items"], f"{path}[{i}]"))
    return errors
