#!/usr/bin/env python3
"""Check featureCounts sample identity and non-negative integer gene counts."""

import argparse
import csv
from pathlib import Path
import re
import sys


def validate(counts: Path, manifest: Path) -> tuple[int, int]:
    with manifest.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["sample", "r1", "r2", "bam"]:
            raise ValueError("Sample manifest requires sample/r1/r2/bam columns")
        samples = list(reader)
    if not samples or any(None in row or any(not value for value in row.values()) for row in samples):
        raise ValueError("Sample manifest is empty or malformed")
    names = [row["sample"] for row in samples]
    bams = [str(Path(row["bam"]).resolve()) for row in samples]
    if len(set(names)) != len(names) or len(set(bams)) != len(bams):
        raise ValueError("Duplicate sample or BAM in manifest")
    with counts.open(encoding="utf-8", newline="") as handle:
        rows = csv.reader((line for line in handle if not line.startswith("#")), delimiter="\t")
        header = next(rows, [])
        if header[:6] != ["Geneid", "Chr", "Start", "End", "Strand", "Length"]:
            raise ValueError("Not a featureCounts gene table: invalid annotation columns")
        actual_bams = [str(Path(value).resolve()) for value in header[6:]]
        if actual_bams != bams:
            raise ValueError("Count sample columns/order do not match the current sample manifest")
        seen = set()
        for number, row in enumerate(rows, start=2):
            if len(row) != len(header) or not row[0] or row[0] in seen:
                raise ValueError(f"Malformed or duplicate gene row at line {number}")
            if any(not re.fullmatch(r"[0-9]+", value) for value in row[6:]):
                raise ValueError(f"Expected non-negative integer counts at line {number}")
            seen.add(row[0])
    if not seen:
        raise ValueError("Count table has no gene rows")
    return len(seen), len(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--sample-manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        genes, samples = validate(args.counts, args.sample_manifest)
    except (OSError, ValueError) as exc:
        print(f"Invalid count output: {exc}", file=sys.stderr)
        return 1
    print(f"Count output verified: {genes} genes, {samples} manifest-matched samples.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
