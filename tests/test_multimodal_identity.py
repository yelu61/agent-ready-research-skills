import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "manage-research-project"
SCRIPT = SKILL / "scripts" / "validate_sample_map.py"
SPEC = importlib.util.spec_from_file_location("sample_map", SCRIPT)
SAMPLE_MAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAMPLE_MAP)


class MultimodalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def table(self, name, rows, fields=None):
        path = self.root / name
        fields = fields or list(rows[0])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields,
                                    delimiter="\t" if path.suffix == ".tsv" else ",")
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def measurements():
        return [dict(measurement_id="rna", donor_id="D1", specimen_id="S1",
                     modality="RNA", timepoint="baseline"),
                dict(measurement_id="atac", donor_id="D1", specimen_id="S1",
                     modality="ATAC", timepoint="baseline")]

    @staticmethod
    def pairs(relation="same_specimen", evidence="synthetic source record"):
        return [dict(left_id="rna", right_id="atac", relation=relation, evidence=evidence)]

    def run_review(self, rows, pairs=None):
        measurements_path = self.table("measurements.tsv", rows)
        pairs_path = self.table("pairs.tsv", pairs) if pairs is not None else None
        return SAMPLE_MAP.review_map(measurements_path, pairs_path)

    @staticmethod
    def codes(report):
        return {issue["code"] for issue in report["issues"]}

    def test_synthetic_paired_unpaired_and_longitudinal_examples(self):
        examples = SKILL / "assets" / "examples"
        for name, extension, paired in (("paired", "tsv", True),
                                        ("unpaired", "tsv", False),
                                        ("longitudinal", "csv", True)):
            with self.subTest(name=name):
                measurements = examples / f"multimodal-{name}-measurements.{extension}"
                pairs = examples / f"multimodal-{name}-pairs.{extension}" if paired else None
                report = SAMPLE_MAP.review_map(measurements, pairs)
                self.assertEqual(report["status"], "valid", report)
                self.assertFalse(report["identity_authenticity_verified"])
                self.assertFalse(report["scientific_validity_assessed"])
                self.assertEqual(report["counts"]["measurements_without_declared_pairs"],
                                 0 if paired else 2)
        bad = SAMPLE_MAP.review_map(examples / "multimodal-conflict-measurements.tsv",
                                    examples / "multimodal-conflict-pairs.tsv")
        self.assertEqual(bad["status"], "invalid")
        self.assertIn("conflicting_parent", self.codes(bad))

    def test_shared_donor_and_equal_row_counts_do_not_infer_pairs(self):
        report = self.run_review(self.measurements())
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["unpaired_measurement_ids"], ["atac", "rna"])
        self.assertEqual(report["counts"]["pair_rows"], 0)

    def test_unknown_biological_identity_remains_review_not_artificial_merge(self):
        rows = self.measurements()
        for row, donor in zip(rows, ("D1", "D2")):
            row.update(donor_id=donor, specimen_id="unknown", timepoint="")
        report = self.run_review(rows)
        self.assertEqual(report["status"], "review")
        self.assertIn("missing_identity", self.codes(report))
        self.assertNotIn("conflicting_parent", self.codes(report))

    def test_duplicate_measurement_and_ambiguous_pair_are_invalid(self):
        rows = self.measurements()
        rows.append(dict(rows[0]))
        report = self.run_review(rows, self.pairs())
        self.assertEqual(report["status"], "invalid")
        self.assertTrue({"duplicate_measurement_id", "ambiguous_measurement"} <= self.codes(report))

    def test_aliquot_section_and_cell_parent_conflicts(self):
        for field in ("aliquot_id", "section_id", "cell_id"):
            with self.subTest(field=field):
                rows = self.measurements()
                rows[1]["specimen_id"] = "S2"
                for row in rows:
                    row[field] = "shared-id"
                    if field == "cell_id":
                        row["cell_namespace"] = "capture-1"
                report = self.run_review(rows)
                self.assertEqual(report["status"], "invalid")
                self.assertIn("conflicting_parent", self.codes(report))

    def test_repeated_library_barcode_does_not_prove_same_cell(self):
        rows = self.measurements()
        for row in rows:
            row["cell_id"] = "AAAC"
        report = self.run_review(rows, self.pairs("same_cell"))
        self.assertEqual(report["status"], "review")
        self.assertIn("missing_cell_namespace", self.codes(report))
        rows[0]["cell_namespace"] = "independent-library-1"
        rows[1]["cell_namespace"] = "independent-library-2"
        report = self.run_review(rows, self.pairs("same_cell"))
        self.assertEqual(report["status"], "invalid")
        self.assertIn("pair_identity_mismatch", self.codes(report))

    def test_cross_section_same_specimen_valid_but_same_cell_requires_review(self):
        rows = self.measurements()
        for number, row in enumerate(rows):
            row.update(section_id=f"S1-section-{number}", cell_id="cell-1",
                       cell_namespace="asserted-registered-cells")
        specimen = self.run_review(rows, self.pairs("same_specimen"))
        self.assertEqual(specimen["status"], "valid")
        cell = self.run_review(rows, self.pairs("same_cell"))
        self.assertEqual(cell["status"], "review")
        self.assertIn("cross_section_cell_identity", self.codes(cell))

    def test_timepoint_and_specimen_relation_boundaries(self):
        rows = self.measurements()
        rows[1].update(timepoint="week-4", specimen_id="S2")
        self.assertEqual(self.run_review(rows, self.pairs("longitudinal"))["status"], "valid")
        donor = self.run_review(rows, self.pairs("same_donor"))
        self.assertEqual(donor["status"], "review")
        self.assertIn("donor_pair_cross_time", self.codes(donor))
        self.assertEqual(self.run_review(rows, self.pairs("same_specimen"))["status"], "invalid")
        rows[1]["timepoint"] = "baseline"
        self.assertEqual(self.run_review(rows, self.pairs("longitudinal"))["status"], "invalid")

    def test_missing_pair_evidence_is_review_and_text_does_not_verify_identity(self):
        report = self.run_review(self.measurements(), self.pairs(evidence=""))
        self.assertEqual(report["status"], "review")
        self.assertIn("missing_pair_evidence", self.codes(report))
        report = self.run_review(self.measurements(), self.pairs(evidence="unchecked assertion"))
        self.assertEqual(report["status"], "valid")
        self.assertFalse(report["identity_authenticity_verified"])

    def test_reverse_duplicate_pair_and_unknown_id(self):
        pairs = self.pairs()
        pairs.append(dict(left_id="atac", right_id="rna", relation="same_specimen", evidence="source"))
        self.assertIn("duplicate_pair", self.codes(self.run_review(self.measurements(), pairs)))
        pairs[1]["right_id"] = "missing"
        self.assertIn("unknown_measurement", self.codes(self.run_review(self.measurements(), pairs)))

    def test_malformed_tables_and_unknown_relation(self):
        for name, content in (("duplicate.tsv", "measurement_id\tmeasurement_id\nA\tB\n"),
                              ("broken.csv", 'measurement_id,donor_id,specimen_id,modality,timepoint\n"unfinished'),
                              ("width.tsv", "measurement_id\tdonor_id\tspecimen_id\tmodality\ttimepoint\nA\tD\n")):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text(content)
                self.assertEqual(SAMPLE_MAP.review_map(path)["status"], "invalid")
        self.assertIn("unknown_relation", self.codes(self.run_review(self.measurements(), self.pairs("same_cluster"))))

    def test_cli_exit_codes_hashes_and_read_only_behavior(self):
        for expected, rows, pairs in ((0, self.measurements(), self.pairs()),
                                      (1, self.measurements(), self.pairs(evidence="")),
                                      (2, self.measurements(), self.pairs("invented"))):
            with self.subTest(expected=expected):
                measurements = self.table("input.tsv", rows)
                links = self.table("links.tsv", pairs)
                before = {path.name: path.read_bytes() for path in self.root.iterdir()}
                result = subprocess.run([sys.executable, str(SCRIPT), "--measurements", str(measurements),
                                         "--pairs", str(links), "--json"], cwd=self.root,
                                        text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, expected, result.stderr)
                report = json.loads(result.stdout)
                self.assertTrue(report["read_only"])
                self.assertEqual(len(report["inputs"]["measurements"]["sha256"]), 64)
                self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})


if __name__ == "__main__":
    unittest.main()
