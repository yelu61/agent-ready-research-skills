"""Executable synthetic regressions; optional numerical dependencies skip honestly."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/scrna-analysis-core/scripts/inspect_anndata.py"
spec = importlib.util.spec_from_file_location("scrna_inspector", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
try:
    import anndata as ad
    import numpy as np
    import pandas as pd
    from scipy import sparse
    NUMERICAL_ERROR = None
except (ImportError, OSError) as exc:
    NUMERICAL_ERROR = str(exc)


class OutputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "input.h5ad"
        self.source.write_bytes(b"synthetic source sentinel")

    def test_input_and_aliases_never_overwritten(self):
        symlink, hardlink = self.root / "symlink.json", self.root / "hardlink.json"
        symlink.symlink_to(self.source)
        os.link(self.source, hardlink)
        for output in (self.source, symlink, hardlink):
            with self.subTest(output=output), self.assertRaises(ValueError):
                audit.write_report(self.source, output, "{}", overwrite=True)
        self.assertEqual(self.source.read_bytes(), b"synthetic source sentinel")

    def test_existing_report_requires_opt_in(self):
        output = self.root / "report.json"
        audit.write_report(self.source, output, '{"old":1}')
        with self.assertRaises(FileExistsError):
            audit.write_report(self.source, output, '{"new":2}')
        self.assertEqual(json.loads(output.read_text()), {"old": 1})
        audit.write_report(self.source, output, '{"new":2}', overwrite=True)
        self.assertEqual(json.loads(output.read_text()), {"new": 2})

    def test_failed_atomic_publish_cleans_temporary(self):
        with patch.object(audit.os, "link", side_effect=OSError("simulated publish failure")):
            with self.assertRaises(OSError):
                audit.write_report(self.source, self.root / "out.json", "{}")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["input.h5ad"])

    def test_cli_rejects_input_collision_before_import(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = audit.main([str(self.source), "--output", str(self.source), "--overwrite-output"])
        self.assertEqual(code, 2)
        self.assertEqual(self.source.read_bytes(), b"synthetic source sentinel")

    def test_handle_closed_when_report_construction_fails(self):
        handle = types.SimpleNamespace(closed=False)
        handle.close = lambda: setattr(handle, "closed", True)
        fake = types.SimpleNamespace(read_h5ad=lambda *a, **k: types.SimpleNamespace(file=handle))
        with patch.dict(sys.modules, {"anndata": fake}), patch.object(audit, "build_report", side_effect=ValueError("bad metadata")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(audit.main([str(self.source)]), 4)
        self.assertTrue(handle.closed)


class DesignTests(unittest.TestCase):
    def test_complete_confounding_specific_contrast(self):
        r = audit.design_connectivity([("a", "tx"), ("b", "ctrl")], ["tx", "ctrl"])
        self.assertFalse(r["contrast"]["estimable"])
        self.assertEqual((r["additive_design_rank"], r["additive_design_columns"]), (2, 3))

    def test_disconnected_does_not_block_every_contrast(self):
        pairs = [(batch, condition) for batch, conditions in [("b1", "AB"), ("b2", "AB"), ("b3", "CD"), ("b4", "CD")] for condition in conditions]
        cross = audit.design_connectivity(pairs, ["A", "C"])
        within = audit.design_connectivity(pairs, ["A", "B"])
        self.assertEqual((cross["additive_design_rank"], cross["additive_design_columns"]), (6, 7))
        self.assertTrue(cross["batch_condition_confounded"])
        self.assertFalse(cross["contrast"]["estimable"])
        self.assertTrue(within["contrast"]["estimable"])

    def test_bridge_makes_contrast_estimable(self):
        r = audit.design_connectivity([("b1", "A"), ("b1", "B"), ("b2", "B"), ("b2", "C")], ["A", "C"])
        self.assertTrue(r["contrast"]["estimable"])
        self.assertFalse(r["batch_condition_confounded"])

    def test_missing_labels_are_unknown_and_typed_nodes_do_not_collide(self):
        self.assertIsNone(audit.design_connectivity([], ["A", "B"])["contrast"]["estimable"])
        r = audit.design_connectivity([("A", "B"), ("B", "C")], ["B", "C"])
        self.assertFalse(r["contrast"]["estimable"])


@unittest.skipIf(NUMERICAL_ERROR is not None, f"Working AnnData/NumPy/SciPy/pandas required: {NUMERICAL_ERROR}")
class AnnDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, rows, counts=None, counts_layer=True):
        obs = pd.DataFrame(rows, columns=["sample_id", "batch", "condition"])
        for key in obs:
            obs[key] = pd.Categorical(obs[key])
        obs.index = [f"cell{i}" for i in range(len(rows))]
        counts = sparse.csr_matrix(np.ones((len(rows), 3))) if counts is None else counts
        a = ad.AnnData(X=counts.copy(), obs=obs)
        if counts_layer:
            a.layers["counts"] = counts.copy()
        path = self.root / "input.h5ad"
        a.write_h5ad(path)
        return path

    def run_audit(self, path, *args):
        original = hashlib.sha256(path.read_bytes()).digest()
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            code = audit.main([str(path), *args])
        self.assertEqual(code, 0)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), original)
        return json.loads(capture.getvalue())

    def test_single_sample_exploration_has_no_artificial_comparison_blocker(self):
        r = self.run_audit(self.fixture([("s1", "b1", "baseline")] * 3))
        self.assertEqual(r["issues"], [])
        self.assertEqual(r["design"]["n_samples"], 1)

    def test_real_h5ad_disconnected_contrast(self):
        rows = [(f"{b}{c}", b, c) for b, cs in [("b1", "AB"), ("b2", "AB"), ("b3", "CD"), ("b4", "CD")] for c in cs]
        path = self.fixture(rows)
        cross = self.run_audit(path, "--contrast", "A", "C")
        within = self.run_audit(path, "--contrast", "A", "B")
        self.assertTrue(any(x["code"] == "disconnected_design" and x["severity"] == "BLOCKED" for x in cross["issues"]))
        self.assertFalse(any(x["severity"] == "BLOCKED" for x in within["issues"]))

    def test_all_missing_sample_labels_are_visible(self):
        r = self.run_audit(self.fixture([(None, "b1", "A"), (None, "b1", "A")]))
        self.assertEqual(r["design"]["n_samples"], 0)
        self.assertTrue(any(x["code"] == "missing_metadata_values" and x["severity"] == "BLOCKED" for x in r["issues"]))

    def test_invalid_counts_reported_without_nonfinite_json(self):
        r = self.run_audit(self.fixture([("s1", "b1", "A"), ("s2", "b1", "A")], np.array([[np.nan, np.inf, -1.0], [0.5, 0, 1]])))
        self.assertIn("invalid_count_values", [x["code"] for x in r["issues"]])
        self.assertIn("fractional_counts", [x["code"] for x in r["issues"]])
        json.dumps(r, allow_nan=False)

    def test_fractional_estimates_not_automatically_rejected_or_rounded(self):
        r = self.run_audit(self.fixture([("s1", "b1", "A")], np.array([[0.5, 2.5, 0]])))
        self.assertEqual([x["severity"] for x in r["issues"] if x["code"] == "fractional_counts"], ["REVIEW"])

    def test_missing_counts_requests_provenance(self):
        r = self.run_audit(self.fixture([("s1", "b1", "A")], counts_layer=False))
        self.assertIn("counts_source_unknown", [x["code"] for x in r["issues"]])

    def test_sampling_denominator_and_tolerance(self):
        values = np.array([[0.0, 0.5]])
        self.assertEqual(audit.matrix_summary(values)["sample_integer_like_fraction"], audit.matrix_summary(sparse.csr_matrix(values))["sample_integer_like_fraction"])
        self.assertEqual(audit.matrix_summary(np.array([[100000.2]]))["sample_integer_like_fraction"], 0.0)
        edge = np.ones((129, 257))
        edge[-1, -1] = -0.5
        self.assertGreater(audit.matrix_summary(edge)["negative_count"], 0)

    def test_specific_contrast_without_batch_is_unknown(self):
        path = self.fixture([("s1", "b1", "A"), ("s2", "b1", "B")])
        r = self.run_audit(path, "--batch-key", "absent", "--contrast", "A", "B")
        self.assertIsNone(r["design"]["contrast"]["estimable"])


if __name__ == "__main__":
    unittest.main()
