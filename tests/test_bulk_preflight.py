from __future__ import annotations

import importlib.util
import copy
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_backend_lock import BACKEND_LOCK, git, make_rnaseq_backend


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

    def test_deg_confirmatory_compatible_is_not_execution_readiness(self) -> None:
        self.assertEqual(self.evaluate()["verdict"], "compatible")

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
        self.assertEqual(locked["verdict"], "blocked")

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
            self.assertEqual(self.run_cli(["verify", "--spec", str(spec_path), "--readiness", str(readiness)]), 3)


class PreflightRegressionTests(unittest.TestCase):
    def test_every_scale_for_count_engines_uses_whitelist(self):
        for task in ("deg", "limma-voom", "time-course"):
            for scale in ("raw-counts", "tpm", "log-tpm", "vst", "rlog", "normalized", "other", "unknown"):
                with self.subTest(task=task, scale=scale):
                    result = PREFLIGHT.evaluate(make_spec(task=task, input_scale=scale), CAPS)
                    self.assertEqual(result["verdict"] == "compatible", scale == "raw-counts")

    def test_formula_interactions_cannot_be_hidden_by_omitted_or_false_flag(self):
        for formula in ("~ condition * time", "~ condition:time", "~ condition/time", "~ (condition + time)^2", "~ condition + time %in% condition", "~ interaction(condition, time)"):
            for flag in ({}, {"interaction": False}):
                with self.subTest(formula=formula, flag=flag):
                    result = PREFLIGHT.evaluate(make_spec(task="time-course", design={"formula": formula, **flag}), CAPS)
                    self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(PREFLIGHT.evaluate(make_spec(task="time-course", design={"formula": "~ patient + condition + time"}), CAPS)["verdict"], "compatible")

    def test_schema_enforces_nested_types_and_unknown_fields(self):
        for override in ({"question": 42}, {"inputs": {"counts": 10}}, {"design": {"formula": "~x", "interaction": "false"}},
                         {"design": {"formula": ["~x"]}}, {"design": {"formula": "~x", "typo": True}},
                         {"split_policy": {"level": "cell"}}, {"design": {}}, {"surprise": True}):
            with self.subTest(override=override):
                self.assertTrue(PREFLIGHT.validate_spec(make_spec(**override)))

    def test_modes_are_sets_not_total_order(self):
        caps = copy.deepcopy(CAPS)
        caps["gates"][0]["allowed_claim_modes"] = ["predictive"]
        for mode in ("descriptive", "exploratory", "confirmatory", "causal", "clinical"):
            self.assertEqual(PREFLIGHT.evaluate(make_spec(claim_class=mode), caps)["verdict"], "blocked")
        self.assertEqual(PREFLIGHT.evaluate(make_spec(claim_class="predictive"), caps)["verdict"], "compatible")


def dump(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


class ReadinessBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = make_rnaseq_backend(self.root / "backend")
        self.lock = BACKEND_LOCK.build_lock("rnaseq-templates", self.backend)
        self.lock_path = self.root / "backend.lock.json"
        dump(self.lock_path, self.lock)
        self.spec = self.root / "spec.json"
        dump(self.spec, make_spec())
        (self.root / "counts.tsv").write_text("gene\ts1\na\t1\n")
        self.evidence = self.root / "review.txt"
        self.evidence.write_text("SYNTHETIC contract fixture; no real RNA-seq numerical validation.\n")
        self.review = self.root / "review.json"
        self.review_doc = {"schema_version": "backend-capability-review/v1", **{k: self.lock[k] for k in ("backend", "source_url", "revision")},
                           "assessor": "test fixture", "reviewed_at": "2026-09-08", "scope": "synthetic gate binding",
                           "catalog_hash": PREFLIGHT.canonical_hash({k: v for k, v in CAPS.items() if k != "bindings"}),
                           "checks": [{"gate_id": "rnaseq.deg", "result": "pass", "kind": "contract-test", "artifact": "review.txt", "sha256": PREFLIGHT.sha256_file(self.evidence)}]}
        dump(self.review, self.review_doc)
        self.caps = self.root / "bound.json"
        self.ready = self.root / "readiness.json"
        self.assertEqual(self.cli("bind-capabilities", "--backend-lock", self.lock_path, "--backend-root", self.backend,
                                  "--review-evidence", self.review, "--output", self.caps), 0)

    def cli(self, *args):
        with patch("sys.argv", ["preflight.py", *map(str, args)]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return PREFLIGHT.main()

    def check(self, mode="execute"):
        return self.cli("check", "--spec", self.spec, "--mode", mode, "--capabilities", self.caps,
                        "--backend-lock", self.lock_path, "--backend-root", self.backend, "--readiness-out", self.ready)

    def verify(self):
        return self.cli("verify", "--spec", self.spec, "--readiness", self.ready)

    def test_exact_revision_binding_is_reusable_without_approval(self):
        self.assertEqual(self.check(), 0)
        record = json.loads(self.ready.read_text())
        self.assertTrue(record["verdict"]["execution_ready"])
        self.assertFalse(record["verdict"]["scientific_certification"])
        self.assertEqual(record["backend_binding"]["lock"], self.lock)
        self.assertEqual(self.verify(), 0)
        self.assertEqual(self.check(), 0)

    def test_review_template_is_not_a_passing_assessment(self):
        template = self.root / "review-template.json"
        self.assertEqual(self.cli("prepare-review", "--backend-lock", self.lock_path, "--gate-id", "rnaseq.deg", "--output", template), 0)
        document = json.loads(template.read_text())
        self.assertEqual(document["revision"], self.lock["revision"])
        self.assertEqual(document["checks"][0]["result"], "not-assessed")
        self.assertEqual(self.cli("bind-capabilities", "--backend-lock", self.lock_path, "--backend-root", self.backend,
                                  "--review-evidence", template, "--output", self.root / "must-not-be-bound.json"), 2)

    def test_no_backend_audit_remains_available_but_execution_is_blocked(self):
        self.assertEqual(self.cli("check", "--spec", self.spec, "--readiness-out", self.ready), 0)
        record = json.loads(self.ready.read_text())
        self.assertEqual(record["verdict"]["verdict"], "plan-only")
        self.assertFalse(record["verdict"]["execution_ready"])
        self.assertEqual(self.verify(), 0)
        self.assertEqual(self.cli("check", "--spec", self.spec, "--mode", "execute", "--readiness-out", self.ready), 3)
        self.assertEqual(self.verify(), 3)

    def test_unbound_catalog_does_not_accept_any_clean_backend(self):
        self.assertEqual(self.cli("check", "--spec", self.spec, "--mode", "execute", "--backend-lock", self.lock_path,
                                  "--backend-root", self.backend, "--readiness-out", self.ready), 3)

    def test_capability_bytes_drift_invalidates_verify(self):
        self.assertEqual(self.check(), 0)
        self.caps.write_text(self.caps.read_text() + "\n")
        self.assertEqual(self.verify(), 4)

    def test_capability_semantics_cannot_be_rebound_to_old_review(self):
        caps = copy.deepcopy(CAPS)
        caps["gates"][0]["allowed_claim_modes"].append("causal")
        changed = self.root / "changed.json"
        dump(changed, caps)
        self.assertEqual(self.cli("bind-capabilities", "--capabilities", changed, "--backend-lock", self.lock_path,
                                  "--backend-root", self.backend, "--review-evidence", self.review,
                                  "--output", self.root / "new-bound.json"), 2)

    def test_review_artifact_drift_invalidates_verify(self):
        self.assertEqual(self.check(), 0)
        self.evidence.write_text("altered test evidence\n")
        self.assertEqual(self.verify(), 4)

    def test_lock_bytes_drift_invalidates_verify_even_same_revision(self):
        self.assertEqual(self.check(), 0)
        self.lock_path.write_text(self.lock_path.read_text() + "\n")
        self.assertEqual(self.verify(), 4)

    def test_actual_backend_revision_drift_is_derived_without_caller_argument(self):
        self.assertEqual(self.check(), 0)
        (self.backend / "RNAseq_lib/core.R").write_text("new revision\n")
        git(self.backend, "add", "RNAseq_lib/core.R")
        git(self.backend, "commit", "-m", "new")
        self.assertEqual(self.verify(), 4)

    def test_dirty_checkout_invalidates_verify(self):
        self.assertEqual(self.check(), 0)
        (self.backend / "RNAseq_lib/core.R").write_text("dirty source\n")
        self.assertEqual(self.verify(), 4)

    def test_schema_and_evaluator_drift_are_detected_in_copied_skill(self):
        # Mutate isolated copies, never the skill being developed.
        for relative in ("assets/schemas/bulk-analysis-spec-v1.schema.json", "scripts/analysis_contract.py", "scripts/prediction_evidence.py", "scripts/preflight.py"):
            with self.subTest(relative=relative):
                copy_root = self.root / ("copy-" + Path(relative).name)
                shutil.copytree(PREFLIGHT_PATH.parent.parent, copy_root)
                runner = copy_root / "scripts/preflight.py"
                command = [sys.executable, "-B", str(runner)]
                args = ["--spec", str(self.spec), "--readiness-out", str(self.ready)]
                self.assertEqual(subprocess.run(command + ["check"] + args, capture_output=True).returncode, 0)
                changed = copy_root / relative
                changed.write_text(changed.read_text() + "\n")
                self.assertEqual(subprocess.run(command + ["verify", "--spec", str(self.spec), "--readiness", str(self.ready)], capture_output=True).returncode, 4)


class PredictionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = {"method": "lasso_cox", "transform": "log2p1", "features": ["a", "b"],
                      "coefficients": {"a": 0.5, "b": -0.5}, "covariates": [], "cutoff": 0.2}
        dump(self.root / "model.json", self.model)
        ids = [f"v{x}" for x in range(20)]
        (self.root / "expression.tsv").write_text("gene\t" + "\t".join(ids) + "\na\t" + "\t".join(["1"] * 20) + "\nb\t" + "\t".join(["2"] * 20) + "\n")
        (self.root / "clinical.tsv").write_text("sample_id\tsurvival_time\tevent\n" + "".join(f"{x}\t10\t1\n" for x in ids))
        self.config = {"task": "external_validate", "model_meta_file": str(self.root / "model.json"),
                       "expression_file": str(self.root / "expression.tsv"), "clinical_file": str(self.root / "clinical.tsv")}
        dump(self.root / "config.json", self.config)
        self.train = {"unit": "patient", "unit_namespace": "reconciled-test-patients", "samples": [{"sample_id": "train1", "patient_id": "p_train"}],
                      "model_meta_sha256": PREFLIGHT.sha256_file(self.root / "model.json")}
        self.valid = {"unit": "patient", "unit_namespace": "reconciled-test-patients", "samples": [{"sample_id": x, "patient_id": "p_" + x} for x in ids],
                      "expression_sha256": PREFLIGHT.sha256_file(self.root / "expression.tsv"), "clinical_sha256": PREFLIGHT.sha256_file(self.root / "clinical.tsv")}
        dump(self.root / "train.json", self.train)
        dump(self.root / "valid.json", self.valid)
        self.spec = make_spec(backend="tcga-toolkit", task="external-validation", claim_class="predictive", input_scale="log-tpm", experimental_unit="patient",
                              split_policy={"level": "patient"}, inputs={"model_meta_file": "model.json", "backend_config": "config.json", "expression_file": "expression.tsv",
                              "clinical_file": "clinical.tsv", "training_units": "train.json", "validation_units": "valid.json"})

    def verdict(self):
        return PREFLIGHT.evaluate(self.spec, CAPS, self.root)["verdict"]

    def test_complete_locked_files_and_disjoint_patients_are_compatible(self):
        self.assertEqual(self.verdict(), "compatible")

    def test_patient_overlap_is_blocked_even_with_different_samples(self):
        self.valid["samples"][0]["patient_id"] = "p_train"
        dump(self.root / "valid.json", self.valid)
        self.assertEqual(self.verdict(), "blocked")

    def test_cell_or_sample_split_cannot_claim_patient_prediction(self):
        for unit, level in (("cell", "sample"), ("sample", "patient"), ("patient", "sample")):
            self.spec["experimental_unit"] = unit
            self.spec["split_policy"]["level"] = level
            self.assertEqual(self.verdict(), "blocked")

    def test_unreconciled_patient_namespaces_block(self):
        self.valid["unit_namespace"] = "independent-looking-but-unmapped"
        dump(self.root / "valid.json", self.valid)
        self.assertEqual(self.verdict(), "blocked")

    def test_model_coefficients_and_training_provenance_are_required(self):
        for key in ("coefficients", "transform", "cutoff"):
            with self.subTest(key=key):
                model = dict(self.model)
                del model[key]
                dump(self.root / "model.json", model)
                self.assertEqual(self.verdict(), "blocked")

    def test_clinical_covariates_not_reproduced_by_backend_are_blocked(self):
        self.model["covariates"] = ["age"]
        dump(self.root / "model.json", self.model)
        self.assertEqual(self.verdict(), "blocked")

    def test_backend_config_cannot_silently_override_model(self):
        for key, value in (("weight_file", "different.csv"), ("cutoff", 42), ("feature_genes", ["a"])):
            self.config[key] = value
            dump(self.root / "config.json", self.config)
            self.assertEqual(self.verdict(), "blocked")
            del self.config[key]

    def test_altered_validation_membership_or_matrix_is_blocked(self):
        self.valid["samples"][0]["sample_id"] = "missing_in_matrix"
        dump(self.root / "valid.json", self.valid)
        self.assertEqual(self.verdict(), "blocked")

    def test_rehashed_missing_feature_still_blocked(self):
        expression = self.root / "expression.tsv"
        expression.write_text(expression.read_text().replace("\nb\t", "\nc\t"))
        self.valid["expression_sha256"] = PREFLIGHT.sha256_file(expression)
        dump(self.root / "valid.json", self.valid)
        self.assertEqual(self.verdict(), "blocked")


if __name__ == "__main__":
    unittest.main()
