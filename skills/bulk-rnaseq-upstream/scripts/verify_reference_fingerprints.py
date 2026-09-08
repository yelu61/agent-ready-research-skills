#!/usr/bin/env python3
"""Verify frozen reference bytes and identities; never invent missing provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import re
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.reader(handle, delimiter="\t")
        if next(rows, None) != ["key", "value"]:
            raise ValueError(f"Invalid metadata header: {path}")
        result = {}
        for row in rows:
            if len(row) != 2 or not row[0] or not row[1] or row[0] in result:
                raise ValueError(f"Empty, malformed or duplicate metadata row in {path}")
            result[row[0]] = row[1]
    if result.get("bundle_schema_version") != "2":
        raise ValueError("Reference metadata requires schema 2 with verified index fingerprints; "
                         "review legacy build provenance before migrating, or rebuild in a new bundle")
    return result


def required(meta: dict[str, str], key: str) -> str:
    value = meta.get(key, "")
    if not value or value in {"UNAVAILABLE", "UNRECORDED"}:
        raise ValueError(f"Missing recorded metadata: {key}")
    return value


def fingerprint(meta: dict[str, str], key: str, path: Path) -> None:
    expected = required(meta, key)
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"Invalid SHA-256 for {key}")
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty reference file: {path}")
    if sha256(path) != expected:
        raise ValueError(f"Reference checksum mismatch: {path} ({key})")


def verify_hisat2(root: Path, prefix: Path) -> None:
    meta = metadata(root / "reference.meta.tsv")
    for key in ("reference_id", "annotation_id"):
        required(meta, key)
    if required(meta, "index_prefix") != prefix.name:
        raise ValueError("Requested index prefix does not match metadata")
    suffix = required(meta, "index_suffix")
    if suffix not in {"ht2", "ht2l"}:
        raise ValueError("Invalid recorded HISAT2 index suffix")
    for key, name in (("fasta_sha256", "genome.fa"), ("fai_sha256", "genome.fa.fai"),
                      ("gtf_sha256", "genes.gtf"), ("bed12_sha256", "genes.bed12")):
        fingerprint(meta, key, root / name)
    other_suffix = "ht2l" if suffix == "ht2" else "ht2"
    if any(Path(f"{prefix}.{part}.{other_suffix}").exists() for part in range(1, 9)):
        raise ValueError("Mixed HISAT2 index formats; use a bundle with one recorded index set")
    for part in range(1, 9):
        fingerprint(meta, f"index_{part}_sha256", Path(f"{prefix}.{part}.{suffix}"))


def verify_xengsort(prefix: Path, identities: dict[str, str]) -> None:
    meta = metadata(Path(f"{prefix}.manifest.tsv"))
    if identities["host_label"] == identities["graft_label"]:
        raise ValueError("Host and graft labels must be distinct")
    for key, expected in identities.items():
        if required(meta, key) != expected:
            raise ValueError(f"Xengsort identity mismatch for {key}: expected {expected}, recorded {meta[key]}")
    for side in ("host", "graft"):
        count = required(meta, f"{side}_fasta_count")
        if not re.fullmatch(r"[1-9][0-9]*", count):
            raise ValueError(f"Invalid {side} FASTA count")
        for number in range(1, int(count) + 1):
            required(meta, f"{side}_fasta_{number}")
            if not re.fullmatch(r"[0-9a-f]{64}", required(meta, f"{side}_fasta_{number}_sha256")):
                raise ValueError(f"Missing source FASTA fingerprint for {side} {number}")
    for suffix in ("hash", "info"):
        fingerprint(meta, f"index_{suffix}_sha256", Path(f"{prefix}.{suffix}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="kind", required=True)
    hisat2 = commands.add_parser("hisat2")
    hisat2.add_argument("reference", type=Path)
    hisat2.add_argument("prefix", type=Path)
    xengsort = commands.add_parser("xengsort")
    xengsort.add_argument("prefix", type=Path)
    for key in ("host-label", "graft-label", "host-reference-id", "graft-reference-id"):
        xengsort.add_argument("--" + key, required=True)
    args = parser.parse_args()
    try:
        if args.kind == "hisat2":
            verify_hisat2(args.reference, args.prefix)
        else:
            verify_xengsort(args.prefix, {key: getattr(args, key) for key in
                            ("host_label", "graft_label", "host_reference_id", "graft_reference_id")})
    except (OSError, ValueError) as exc:
        print(f"Invalid reference: {exc}", file=sys.stderr)
        return 1
    print("Reference identities and file SHA-256 fingerprints verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
