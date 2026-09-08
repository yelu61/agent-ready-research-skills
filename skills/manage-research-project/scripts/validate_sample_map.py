#!/usr/bin/env python3
"""Read-only consistency review of declared measurement identities and pairs."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys


MEASUREMENT_FIELDS = ("measurement_id", "donor_id", "specimen_id", "modality", "timepoint")
PAIR_FIELDS = ("left_id", "right_id", "relation")
RELATIONS = {"same_donor", "same_specimen", "same_cell", "longitudinal"}
UNKNOWN = {"", "na", "n/a", "unknown", "todo", "none", "null"}


def known(value):
    return value.strip().lower() not in UNKNOWN


def review_map(measurements_path, pairs_path=None):
    """Return documentary consistency, never verified biological identity."""
    report = {
        "schema": "research-sample-map-review/v1",
        "status": "valid",
        "read_only": True,
        "identity_authenticity_verified": False,
        "scientific_validity_assessed": False,
        "inputs": {},
        "counts": {},
        "issues": [],
    }

    def issue(severity, code, table, row, message):
        report["issues"].append({"severity": severity, "code": code,
                                 "table": table, "row": row, "message": message})

    def read_table(path, label, required):
        try:
            path = Path(path)
            raw = path.read_bytes()
            report["inputs"][label] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
            if path.suffix.lower() not in {".tsv", ".csv"}:
                raise ValueError("Use a .tsv or .csv extension to declare the delimiter.")
            text = raw.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""),
                                delimiter="\t" if path.suffix.lower() == ".tsv" else ",",
                                strict=True)
            header = next(reader, [])
            header = [field.strip() for field in header]
            if not header or any(not field for field in header) or len(set(header)) != len(header):
                raise ValueError("Header names must be nonempty and unique.")
            missing = set(required) - set(header)
            if missing:
                raise ValueError("Missing required headers: " + ", ".join(sorted(missing)))
            rows = []
            for values in reader:
                if not values or all(not value.strip() for value in values):
                    continue
                if len(values) != len(header):
                    issue("error", "row_width", label, reader.line_num,
                          "Number of fields differs from the header.")
                    continue
                rows.append((reader.line_num, dict(zip(header, (value.strip() for value in values)))))
            return rows
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            issue("error", "unreadable_table", label, None, str(exc))
            return []

    rows = read_table(measurements_path, "measurements", MEASUREMENT_FIELDS)
    pairs = read_table(pairs_path, "pairs", PAIR_FIELDS) if pairs_path else []
    measurements, duplicates = {}, set()
    # Each stable identity belongs to one known biological parent. Unknown
    # values do not create artificial shared identities or parent conflicts.
    parents = {}

    def parent(child_type, child, parent_type, parent, row):
        if not all(known(value) for value in child) or not known(parent):
            return
        key = (child_type, child, parent_type)
        previous = parents.get(key)
        if previous and previous[0] != parent:
            issue("error", "conflicting_parent", "measurements", row,
                  f"{child_type} {child!r} has conflicting {parent_type}: "
                  f"{previous[0]!r} (row {previous[1]}) and {parent!r}.")
        else:
            parents[key] = (parent, row)

    for row, item in rows:
        identity = item["measurement_id"]
        if not known(identity):
            issue("error", "missing_measurement_id", "measurements", row,
                  "Every measurement needs a stable unique ID.")
        elif identity in measurements:
            duplicates.add(identity)
            issue("error", "duplicate_measurement_id", "measurements", row,
                  f"Duplicate measurement_id {identity!r}; do not silently merge rows.")
        else:
            measurements[identity] = item
        if not known(item["modality"]):
            issue("error", "missing_modality", "measurements", row,
                  "Declare what was measured; modality cannot be inferred from the ID.")
        for field in ("donor_id", "specimen_id", "timepoint"):
            if not known(item[field]):
                issue("review", "missing_identity", "measurements", row,
                      f"{field} is unknown; affected matching claims remain unresolved.")
        specimen = item["specimen_id"]
        parent("specimen", (specimen,), "donor_id", item["donor_id"], row)
        parent("specimen", (specimen,), "timepoint", item["timepoint"], row)
        for child_type in ("aliquot", "section"):
            child_id = item.get(child_type + "_id", "")
            parent(child_type, (child_id,), "specimen_id", specimen, row)
            parent(child_type, (child_id,), "donor_id", item["donor_id"], row)
        cell = (item.get("cell_namespace", ""), item.get("cell_id", ""))
        parent("cell", cell, "specimen_id", specimen, row)
        parent("cell", cell, "donor_id", item["donor_id"], row)
        if known(cell[1]) and not known(cell[0]):
            issue("review", "missing_cell_namespace", "measurements", row,
                  "cell_id without a namespace is not comparable across assays; "
                  "repeated library barcodes do not establish the same cell.")

    paired, seen_pairs = set(), set()
    for row, pair in pairs:
        left_id, right_id, relation = (pair[field] for field in PAIR_FIELDS)
        key = (tuple(sorted((left_id, right_id))), relation)
        if key in seen_pairs:
            issue("error", "duplicate_pair", "pairs", row,
                  "Repeated relation for the same unordered measurement pair.")
        seen_pairs.add(key)
        if relation not in RELATIONS:
            issue("error", "unknown_relation", "pairs", row,
                  f"relation must be one of {', '.join(sorted(RELATIONS))}.")
            continue
        if left_id == right_id:
            issue("error", "self_pair", "pairs", row,
                  "A pairing relation must name two different measurements.")
            continue
        missing = [value for value in (left_id, right_id) if value not in measurements]
        if missing:
            issue("error", "unknown_measurement", "pairs", row,
                  f"Unknown measurement IDs: {missing!r}.")
            continue
        if left_id in duplicates or right_id in duplicates:
            issue("error", "ambiguous_measurement", "pairs", row,
                  "A duplicate measurement ID makes this pair ambiguous.")
            continue
        paired.update((left_id, right_id))
        left, right = measurements[left_id], measurements[right_id]
        if not known(pair.get("evidence", "")):
            issue("review", "missing_pair_evidence", "pairs", row,
                  "Record the source of the matching assertion; names, row order "
                  "and equal cell counts are not matching evidence.")

        def compare(field, must_equal=True, mismatch_severity="error"):
            a, b = left.get(field, ""), right.get(field, "")
            if not known(a) or not known(b):
                issue("review", "unresolved_pair_identity", "pairs", row,
                      f"Cannot assess {relation}: {field} is unknown.")
            elif (a == b) != must_equal:
                issue(mismatch_severity, "pair_identity_mismatch", "pairs", row,
                      f"{relation} requires {field} to be "
                      f"{'equal' if must_equal else 'different'}; got {a!r} and {b!r}.")

        compare("donor_id")
        if relation == "longitudinal":
            compare("timepoint", must_equal=False)
            if known(left["specimen_id"]) and left["specimen_id"] == right["specimen_id"]:
                issue("error", "longitudinal_same_specimen", "pairs", row,
                      "Longitudinal collection requires distinct collection specimens; "
                      "reassaying a stored specimen is not a new biological timepoint.")
        elif relation in {"same_specimen", "same_cell"}:
            compare("specimen_id")
            compare("timepoint")
        elif (known(left["timepoint"]) and known(right["timepoint"])
              and left["timepoint"] != right["timepoint"]):
            issue("review", "donor_pair_cross_time", "pairs", row,
                  "Same donor is compatible with different timepoints, but does not "
                  "establish time-matched pairing. Declare longitudinal if that is intended.")
        if relation == "same_cell":
            compare("cell_namespace")
            compare("cell_id")
            a, b = left.get("section_id", ""), right.get("section_id", "")
            if known(a) and known(b) and a != b:
                issue("review", "cross_section_cell_identity", "pairs", row,
                      "Different sections need explicit spatial/identity review; a "
                      "shared specimen and matching barcode cannot establish the same cell.")

    if not rows and not any(issue["severity"] == "error" for issue in report["issues"]):
        issue("review", "empty_measurements", "measurements", None,
              "No measurements were registered.")
    report["counts"] = {"measurement_rows": len(rows), "unique_measurements": len(measurements),
                        "pair_rows": len(pairs), "measurements_without_declared_pairs":
                        len(set(measurements) - paired)}
    report["unpaired_measurement_ids"] = sorted(set(measurements) - paired)
    report["interpretation"] = (
        "Checks recorded identities and explicit matching assertions only. "
        "Unpaired measurements are allowed; no pairing is inferred. A valid table "
        "does not verify biological identity, independence, batch correction, "
        "statistical design or scientific conclusions. Evidence text is not verified."
    )
    severities = {item["severity"] for item in report["issues"]}
    report["status"] = "invalid" if "error" in severities else "review" if "review" in severities else "valid"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True, help="Measurement identity .tsv or .csv")
    parser.add_argument("--pairs", type=Path, help="Optional explicit pairing .tsv or .csv")
    parser.add_argument("--json", action="store_true", help="Emit the complete review as JSON")
    args = parser.parse_args(argv)
    report = review_map(args.measurements, args.pairs)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Sample map:", report["status"])
        print(report["interpretation"])
        print(json.dumps(report["counts"], sort_keys=True))
        for item in report["issues"]:
            print(f"{item['severity']} {item['table']}:{item['row']} "
                  f"{item['code']}: {item['message']}")
    return {"valid": 0, "review": 1, "invalid": 2}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
