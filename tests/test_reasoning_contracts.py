"""Actual structure/ID behavior in independently installable handoff checkers."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [ROOT / "skills" / name for name in ("scientific-reasoning", "scrna-analysis-core")]


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = []
        for i, package in enumerate(PACKAGES):
            spec = importlib.util.spec_from_file_location(f"handoff_{i}", package / "scripts/validate_handoff.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.validators.append(module.validate)
        cls.brief = json.loads((PACKAGES[0] / "assets/examples/paired-response-brief.json").read_text())
        cls.review = json.loads((PACKAGES[0] / "assets/examples/paired-response-review.json").read_text())

    def test_examples_validate_in_each_independent_package(self):
        for validate in self.validators:
            self.assertEqual(validate(self.brief), [])
            self.assertEqual(validate(self.review, self.brief), [])

    def test_question_and_evidence_identity_are_preserved(self):
        for field, value in (("question_id", "changed"), ("evidence_coverage", self.review["evidence_coverage"][:1])):
            changed = copy.deepcopy(self.review)
            changed[field] = value
            for validate in self.validators:
                self.assertTrue(validate(changed, self.brief))
        duplicate = copy.deepcopy(self.review)
        duplicate["evidence_coverage"].append(duplicate["evidence_coverage"][0])
        for validate in self.validators:
            self.assertTrue(validate(duplicate, self.brief))

    def test_unknown_scientific_unit_is_explicitly_allowed(self):
        brief = copy.deepcopy(self.brief)
        brief["estimand"]["experimental_unit"] = None
        for validate in self.validators:
            self.assertEqual(validate(brief), [])

    def test_old_draft_requires_explicit_migration(self):
        old = copy.deepcopy(self.review)
        old["schema_version"] = "0.1-draft"
        for validate in self.validators:
            self.assertTrue(validate(old))

    def test_plan_is_not_accepted_as_run_record(self):
        run = {"schema_name": "RunEvidence", "schema_version": "0.2-draft", "question_id": "Q7",
               "evidence_id": "E1", "run_id": "synthetic-test-run", "execution_status": "completed",
               "quality_status": "REVIEW", "artifact": {"path_or_key": "synthetic:test-log"},
               "method": {"name": "synthetic fixture", "version": None},
               "result": {"summary": "This is a schema test, not experimental evidence."}}
        for validate in self.validators:
            self.assertEqual(validate(run, self.brief), [])
            planned = copy.deepcopy(run)
            planned["execution_status"] = "planned"
            self.assertTrue(validate(planned, self.brief))
            not_run = copy.deepcopy(run)
            not_run["quality_status"] = "NOT_RUN"
            self.assertTrue(validate(not_run, self.brief))

    def test_malformed_values_rejected_without_crashing(self):
        cases = [None, [], {"schema_name": []}]
        for field in ("stages", "overall_status", "evidence_coverage", "claim_boundary"):
            changed = copy.deepcopy(self.review)
            changed[field] = {"unexpected": []}
            cases.append(changed)
        for validate in self.validators:
            for case in cases:
                self.assertTrue(validate(case))
            broken_upstream = copy.deepcopy(self.brief)
            broken_upstream["required_evidence"] = None
            self.assertTrue(validate(self.review, broken_upstream))

    def test_same_version_has_same_behavior_and_contract_examples(self):
        mutations = [self.review, self.brief, {}, {"schema_name": "Unknown"}]
        for payload in mutations:
            self.assertEqual(self.validators[0](payload), self.validators[1](payload))
        for name in ("paired-response-brief.json", "paired-response-review.json"):
            self.assertEqual(json.loads((PACKAGES[0] / "assets/examples" / name).read_text()),
                             json.loads((PACKAGES[1] / "assets/examples" / name).read_text()))

    def test_installed_alone_cli_has_no_sibling_dependency(self):
        for package in PACKAGES:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                installed = root / "installed-skill"
                shutil.copytree(package, installed, ignore=shutil.ignore_patterns("__pycache__"))
                command = [sys.executable, str(installed / "scripts/validate_handoff.py"),
                           str(installed / "assets/examples/paired-response-review.json"), "--brief",
                           str(installed / "assets/examples/paired-response-brief.json")]
                process = subprocess.run(command, cwd=root, text=True, capture_output=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertTrue(json.loads(process.stdout)["valid_structure"])


if __name__ == "__main__":
    unittest.main()
