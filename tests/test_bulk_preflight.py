from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = (
    ROOT
    / "skills"
    / "bulk-rnaseq-analysis"
    / "scripts"
    / "preflight.py"
)

SPEC = importlib.util.spec_from_file_location("bulk_rnaseq_preflight", PREFLIGHT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load preflight from {PREFLIGHT_PATH}")
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)

CAPS = json.loads(
    (ROOT / "skills" / "bulk-rnaseq-analysis" / "assets" / "backend-capabilities.json")
    .read_text(encoding="utf-8")
)


def make_spec(**overrides) -> dict:
    spec = {
        "question": "Is gene X differentially expressed?",
        "claim_class": "confirmatory",
        "backend": "rnaseq-templates",
        "task": "deg",
        "input_scale": "raw-counts",
        "experimental_unit": "sample",
        "design": {"formula": "~ condition", "contrast": ["Treat", "Ctrl"]},
        "inputs": {"counts": "counts.tsv"},
    }
    spec.update(overrides)
    return spec


class PreflightSpecValidationTests(unittest.TestCase):
    def test_valid_spec_passes(self) -> None:
        self.assertEqual(PREFLIGHT.validate_spec(make_spec()), [])

    def test_missing_required_field(self) -> None:
        spec = make_spec()
        del spec["design"]
        self.assertTrue(any("design" in e for e in PREFLIGHT.validate_spec(spec)))

    def test_bad_enum_rejected(self) -> None:
        errors = PREFLIGHT.validate_spec(make_spec(claim_class="definitely-true"))
        self.assertTrue(any("claim_class" in e for e in errors))


class PreflightGateTests(unittest.TestCase):
    def evaluate(self, **overrides) -> dict:
        return PREFLIGHT.evaluate(make_spec(**overrides), CAPS)

    def test_deg_confirmatory_ready(self) -> None:
        self.assertEqual(self.evaluate()["verdict"], "ready")

    def test_tpm_deg_blocked(self) -> None:
        verdict = self.evaluate(input_scale="tpm")
        self.assertEqual(verdict["verdict"], "blocked")
        self.assertIn("raw-counts", verdict["min_fix"])

    def test_timecourse_interaction_blocked(self) -> None:
        verdict = self.evaluate(
            task="time-course",
            design={"formula": "~ condition * time", "time": True, "interaction": True},
        )
        self.assertEqual(verdict["verdict"], "blocked")
        self.assertEqual(verdict["gate_id"], "rnaseq.time-course")

    def test_prognostic_predictive_blocked(self) -> None:
        verdict = self.evaluate(backend="tcga-toolkit", task="prognostic-model",
                                claim_class="predictive")
        self.assertEqual(verdict["verdict"], "blocked")

    def test_external_validation_predictive_requires_locks(self) -> None:
        base = dict(backend="tcga-toolkit", task="external-validation", claim_class="predictive")
        unlocked = self.evaluate(**base)
        self.assertEqual(unlocked["verdict"], "blocked")
        locked = self.evaluate(
            **base,
            split_policy={"level": "patient", "locked_features": True,
                          "locked_transform": True, "locked_cutoff": True},
        )
        self.assertEqual(locked["verdict"], "ready")

    def test_gtex_compare_capped_at_descriptive(self) -> None:
        verdict = self.evaluate(backend="tcga-toolkit", task="gtex-compare",
                                claim_class="exploratory")
        self.assertEqual(verdict["verdict"], "blocked")

    def test_unregistered_task_blocked(self) -> None:
        verdict = self.evaluate(task="rnaseq-clown")
        self.assertEqual(verdict["verdict"], "blocked")
        self.assertIn("no capability gate", verdict["reasons"][0])


class PreflightHashTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> int:
        from unittest.mock import patch
        with patch("sys.argv", ["preflight.py"] + argv):
            return PREFLIGHT.main()

    def test_stale_readiness_detected_on_input_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            counts = root / "counts.tsv"
            counts.write_text("gene\ts1\na\t1\n", encoding="utf-8")
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(make_spec()), encoding="utf-8")
            readiness = root / "readiness.json"

            rc = self.run_cli(["check", "--spec", str(spec_path),
                               "--capabilities", str(ROOT / "skills" / "bulk-rnaseq-analysis" / "assets" / "backend-capabilities.json"),
                               "--readiness-out", str(readiness)])
            self.assertEqual(rc, 0)
            self.assertEqual(
                self.run_cli(["verify", "--spec", str(spec_path), "--readiness", str(readiness)]),
                0,
            )

            counts.write_text("gene\ts1\na\t2\n", encoding="utf-8")
            self.assertEqual(
                self.run_cli(["verify", "--spec", str(spec_path), "--readiness", str(readiness)]),
                4,
            )

    def test_blocked_spec_exits_3_and_still_writes_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "counts.tsv").write_text("gene\ts1\na\t1\n", encoding="utf-8")
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(make_spec(input_scale="tpm")), encoding="utf-8")
            readiness = root / "readiness.json"
            rc = self.run_cli(["check", "--spec", str(spec_path), "--readiness-out", str(readiness)])
            self.assertEqual(rc, 3)
            record = json.loads(readiness.read_text(encoding="utf-8"))
            self.assertEqual(record["verdict"]["verdict"], "blocked")


if __name__ == "__main__":
    unittest.main()
