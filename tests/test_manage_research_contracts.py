from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "manage-research-project"
SCAFFOLD = SKILL / "scripts" / "scaffold_project.py"
AUDIT = SKILL / "scripts" / "audit_project.py"
BUILD_SOURCE = SKILL / "scripts" / "build_source_manifest.py"
VERIFY_SOURCE = SKILL / "scripts" / "verify_source_manifest.py"
VALIDATE_READINESS = SKILL / "scripts" / "validate_readiness.py"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_sha256(value: dict[str, str] | str) -> str:
    if isinstance(value, dict):
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    else:
        payload = value.strip() + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scaffold(target: Path, profile: str = "research") -> None:
    result = run_script(
        SCAFFOLD,
        str(target),
        "--profile",
        profile,
        "--apply",
        "--json",
    )
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)


def build_ready_fixture(target: Path) -> tuple[Path, dict, dict]:
    scaffold(target)
    raw = target / "data" / "raw" / "input.tsv"
    raw.write_text("sample\tvalue\nS1\t1\n", encoding="utf-8")
    source_result = run_script(
        BUILD_SOURCE,
        str(target),
        "--apply",
        "--source-system",
        "fixture",
        "--source-reference",
        "fixture-run-sheet-v1",
        "--acquired-at",
        datetime.now(timezone.utc).isoformat(),
        "--data-freeze-id",
        "freeze-1",
        "--access-level",
        "internal",
        "--subject-id-level",
        "deidentified",
        "--license-or-agreement",
        "fixture-protocol",
        "--json",
    )
    if source_result.returncode:
        raise AssertionError(source_result.stderr or source_result.stdout)
    source_manifest = target / "provenance" / "SOURCE_MANIFEST.json"
    source_document = json.loads(source_manifest.read_text(encoding="utf-8"))
    source_id = source_document["entries"][0]["source_id"]

    policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
    policy = {
        "schema_version": "readiness-gate-policy/v1",
        "policy_id": "fixture-policy",
        "version": "1.0.0",
        "assessor": {"name": "fixture-domain-assessor", "version": "1.0.0"},
        "domain": "test-fixture",
        "applicable_study_types": ["two-group observational fixture"],
        "applicable_data_requirements": ["data_bearing"],
        "methodological_basis": ["fixture-method-v1"],
        "authorizations": [
            {
                "analysis_mode": "exploratory",
                "claim_classes": ["association"],
                "validation_levels": ["sensitivity"],
            }
        ],
        "gates": [
            {
                "gate_id": "G-DESIGN",
                "required_for_ready": True,
                "allow_na": False,
                "requirement": "Independent unit and comparison are explicit.",
                "applicability": "Data-bearing two-group fixture analyses.",
                "evaluation_method": "Inspect the bound domain specification.",
                "pass_condition": "Independent unit and comparison are both explicit.",
                "required_evidence_kinds": ["file"],
                "failure_effect": "block",
            }
        ],
    }
    write_json(policy_path, policy)

    domain_spec_path = target / "analysis" / "specs" / "A-001-domain.json"
    write_json(
        domain_spec_path,
        {
            "schema_version": "fixture-domain-spec/v1",
            "comparison": "group_b_vs_group_a",
        },
    )
    spec_path = target / "analysis" / "specs" / "A-001.json"
    write_json(
        spec_path,
        {
            "schema_version": "research-analysis-spec/v1",
            "analysis_id": "A-001",
            "scope_id": "A-001",
            "question": "Is the fixture outcome associated with group?",
            "intended_use": "exploratory association screening",
            "study_type": "two-group observational fixture",
            "data_requirement": "data_bearing",
            "analysis_mode": "exploratory",
            "requested_claim_class": "association",
            "target_validation_level": "independent_external",
            "input_source_ids": [source_id],
            "independent_unit": "subject",
            "observation_unit": "sample",
            "estimand": "difference in mean fixture outcome between groups",
            "prespecification": "post_hoc",
            "design": {
                "population": "subjects represented in fixture source freeze-1",
                "analysis_set": "all source rows passing the fixture inclusion rule",
                "exposure_or_intervention": "fixture group assignment",
                "comparator": "group A",
                "outcome": "fixture numeric outcome",
                "time_zero": "not_applicable: cross-sectional fixture",
                "follow_up_window": "not_applicable: cross-sectional fixture",
                "effect_measure": "difference in group means",
                "unit_hierarchy": ["subject", "sample"],
                "missingness_and_censoring": "exclude missing outcome; report exclusions",
                "multiplicity_control": "one prespecified fixture comparison",
                "decision_rule": "report estimate and uncertainty without causal language",
                "protocol_deviation_status": "none",
            },
            "domain": "test-fixture",
            "domain_spec": {
                "path": "analysis/specs/A-001-domain.json",
                "sha256": sha256(domain_spec_path),
            },
            "backend_revision": "fixture-backend-1",
            "entry_points": ["scripts/python/analysis.py"],
            "domain_parameters": {"comparison": "group_b_vs_group_a"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    code_file = target / "scripts" / "python" / "analysis.py"
    code_file.write_text("print('fixture')\n", encoding="utf-8")
    code_result = run_script(
        BUILD_SOURCE,
        str(target),
        "--include",
        "scripts/python",
        "--output",
        "provenance/CODE_MANIFEST.json",
        "--source-system",
        "local-project-code",
        "--access-level",
        "internal",
        "--subject-id-level",
        "none",
        "--apply",
        "--json",
    )
    if code_result.returncode:
        raise AssertionError(code_result.stderr or code_result.stdout)
    code_manifest = target / "provenance" / "CODE_MANIFEST.json"
    environment = target / "provenance" / "ENVIRONMENT.lock"
    environment.write_text("fixture-package==1.0\n", encoding="utf-8")

    report_path = target / "analysis" / "readiness" / "A-001.json"
    report = {
        "schema_version": "research-readiness/v1",
        "readiness_id": "READY-A-001-1",
        "analysis_id": "A-001",
        "scope_id": "A-001",
        "intended_use": "exploratory association screening",
        "assessor": {"name": "fixture-domain-assessor", "version": "1.0.0"},
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "source_provenance_status": "verified",
        "readiness_status": "ready",
        "analysis_mode": "exploratory",
        "requested_claim_class": "association",
        "achieved_validation_level": "sensitivity",
        "claim_authorization": "authorized",
        "lifecycle_status": "current",
        "gate_policy": {
            "path": "analysis/specs/fixture-gate-policy.json",
            "sha256": sha256(policy_path),
        },
        "analysis_spec": {
            "path": "analysis/specs/A-001.json",
            "sha256": sha256(spec_path),
        },
        "input_manifest": {
            "path": "provenance/SOURCE_MANIFEST.json",
            "sha256": sha256(source_manifest),
        },
        "input_source_ids": [source_id],
        "code_manifest": {
            "path": "provenance/CODE_MANIFEST.json",
            "sha256": sha256(code_manifest),
        },
        "environment_snapshot": {
            "path": "provenance/ENVIRONMENT.lock",
            "sha256": sha256(environment),
        },
        "code_revision": "fixture-code-1",
        "code_dirty": False,
        "backend_revision": "fixture-backend-1",
        "authorized_claim_classes": ["association"],
        "prohibited_claim_classes": [
            "causal_effect",
            "mechanism",
            "clinical_utility",
        ],
        "claim_boundary_notes": [
            "Report the exploratory association with uncertainty; prose is not machine-authoritative."
        ],
        "gates": [
            {
                "gate_id": "G-DESIGN",
                "required_for_ready": True,
                "status": "PASS",
                "requirement": "Independent unit and comparison are explicit.",
                "evidence": [
                    {
                        "kind": "file",
                        "ref": "analysis/specs/A-001.json",
                        "sha256": sha256(spec_path),
                    }
                ],
                "impact": "",
                "remediation": "",
            }
        ],
    }
    write_json(report_path, report)
    return report_path, report, policy


def validate_current_fixture(
    target: Path, report_path: Path
) -> subprocess.CompletedProcess[str]:
    return run_script(
        VALIDATE_READINESS,
        str(target),
        str(report_path.relative_to(target)),
        "--require-ready",
        "--current-code-revision",
        "fixture-code-1",
        "--current-code-dirty",
        "false",
        "--current-backend-revision",
        "fixture-backend-1",
        "--json",
    )


class ManageResearchContractTests(unittest.TestCase):
    def test_research_scaffold_and_audit_keep_science_unassessed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold(target)
            self.assertTrue((target / "analysis" / "specs").is_dir())
            self.assertTrue((target / "analysis" / "readiness").is_dir())
            self.assertTrue((target / "docs" / "READINESS.md").is_file())
            self.assertTrue((target / "provenance" / "ARTIFACTS.tsv").is_file())
            self.assertTrue((target / "provenance" / "RUNS.tsv").is_file())

            result = run_script(AUDIT, str(target), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["schema_version"], "project-structure-audit/v2")
            self.assertEqual(report["audit_kind"], "structure")
            self.assertEqual(report["structure_status"], "pass")
            self.assertEqual(report["source_integrity"], "not_assessed")
            self.assertEqual(report["scientific_readiness"], "not_assessed")

    def test_scaffold_reports_path_type_conflict_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            target.mkdir()
            blocker = target / "docs"
            blocker.write_text("preserve\n", encoding="utf-8")
            result = run_script(
                SCAFFOLD,
                str(target),
                "--mode",
                "retrofit",
                "--apply",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertTrue(report["conflicts"])
            self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((target / "AGENTS.md").exists())

    def test_source_manifest_dry_run_verify_and_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "data" / "raw").mkdir(parents=True)
            raw = target / "data" / "raw" / "input.txt"
            raw.write_text("original\n", encoding="utf-8")

            dry_run = run_script(BUILD_SOURCE, str(target), "--json")
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertFalse((target / "provenance" / "SOURCE_MANIFEST.json").exists())
            applied = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(applied.returncode, 0, applied.stderr)

            verified = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(verified.returncode, 0, verified.stderr)
            verified_report = json.loads(verified.stdout)
            self.assertEqual(verified_report["manifest_contract_status"], "valid")
            self.assertEqual(verified_report["source_integrity_status"], "pass")

            raw.write_text("changed\n", encoding="utf-8")
            changed = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(changed.returncode, 1)
            codes = {item["code"] for item in json.loads(changed.stdout)["findings"]}
            self.assertIn("source-hash-changed", codes)

    def test_source_manifest_path_escape_is_contract_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            applied = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            manifest = target / "provenance" / "SOURCE_MANIFEST.json"
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["entries"][0]["path"] = "../outside.txt"
            write_json(manifest, document)

            result = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["manifest_contract_status"], "invalid")
            self.assertEqual(report["source_integrity_status"], "not_assessed")
            self.assertIn(
                "source-path-unsafe", {item["code"] for item in report["findings"]}
            )

    def test_source_manifest_rejects_symlink_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            actual_raw = target / "actual" / "raw"
            actual_raw.mkdir(parents=True)
            (actual_raw / "input.txt").write_text("x\n", encoding="utf-8")
            (target / "data").symlink_to(target / "actual", target_is_directory=True)

            result = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((target / "provenance" / "SOURCE_MANIFEST.json").exists())

    def test_source_manifest_rejects_symlinked_output_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "project"
            outside = base / "outside"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            outside.mkdir()
            (target / "provenance").symlink_to(outside, target_is_directory=True)

            result = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((outside / "SOURCE_MANIFEST.json").exists())

    def test_source_context_null_enum_is_contract_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            built = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(built.returncode, 0, built.stderr)
            manifest = target / "provenance" / "SOURCE_MANIFEST.json"
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["source_context"]["access_level"] = None
            write_json(manifest, document)
            verified = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(verified.returncode, 1)
            output = json.loads(verified.stdout)
            self.assertEqual(output["manifest_contract_status"], "invalid")
            self.assertIn(
                "source-access-level",
                {item["code"] for item in output["findings"]},
            )

    def test_source_id_is_bound_to_path_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            built = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(built.returncode, 0, built.stderr)
            manifest_path = target / "provenance" / "SOURCE_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["entries"][0]["source_id"] = "SRC-FORGED000000"
            write_json(manifest_path, manifest)
            result = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "source-id-binding",
                {item["code"] for item in json.loads(result.stdout)["findings"]},
            )

    def test_source_ids_change_when_bytes_change_at_same_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ids: list[str] = []
            for name, content in (("one", "first\n"), ("two", "second\n")):
                target = Path(temporary) / name
                (target / "data" / "raw").mkdir(parents=True)
                (target / "data" / "raw" / "input.txt").write_text(
                    content, encoding="utf-8"
                )
                result = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                document = json.loads(
                    (target / "provenance" / "SOURCE_MANIFEST.json").read_text(
                        encoding="utf-8"
                    )
                )
                ids.append(document["entries"][0]["source_id"])
            self.assertNotEqual(ids[0], ids[1])

    def test_audit_rejects_unsafe_tsv_target_and_handles_extra_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold(target)
            manifest = target / "TEST_MANIFEST.tsv"
            manifest.write_text(
                "artifact_path\tnotes\n../outside.txt\tx\nfile:///etc/passwd\tx\ndata/raw/missing.txt\tx\textra\n",
                encoding="utf-8",
            )
            result = run_script(AUDIT, str(target), "--json")
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("manifest-target-unsafe", codes)
            self.assertIn("manifest-target", codes)

    def test_audit_rejects_canonical_symlinks_and_malformed_notebooks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "project"
            scaffold(target)
            outside_agents = base / "outside-agents.md"
            outside_agents.write_text(
                "Never modify data/raw; leaked /Users/outside/path.\n",
                encoding="utf-8",
            )
            (target / "AGENTS.md").unlink()
            (target / "AGENTS.md").symlink_to(outside_agents)
            (target / "notebooks" / "bad.ipynb").write_text("[]\n", encoding="utf-8")

            raw = target / "data" / "raw" / "input.tsv"
            raw.write_text("x\n", encoding="utf-8")
            built = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(built.returncode, 0, built.stderr)
            manifest = target / "provenance" / "SOURCE_MANIFEST.json"
            outside_manifest = base / "outside-source-manifest.json"
            manifest.replace(outside_manifest)
            manifest.symlink_to(outside_manifest)

            result = run_script(AUDIT, str(target), "--json")
            self.assertEqual(result.returncode, 1, result.stderr)
            output = json.loads(result.stdout)
            codes = {item["code"] for item in output["findings"]}
            self.assertIn("path-symlink", codes)
            self.assertIn("source-read", codes)
            self.assertNotIn("absolute-path", codes)
            self.assertEqual(output["source_manifest_contract"], "not_assessed")

    def test_source_review_requires_explicit_allow_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            built = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(built.returncode, 0, built.stderr)
            manifest_path = target / "provenance" / "SOURCE_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["entries"][0]["hash_status"] = "not_permitted"
            manifest["entries"][0]["access_reference"] = "controlled-store:fixture"
            write_json(manifest_path, manifest)

            review = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(review.returncode, 1)
            self.assertEqual(json.loads(review.stdout)["integrity_status"], "review")
            allowed = run_script(VERIFY_SOURCE, str(target), "--allow-review", "--json")
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_policy_bound_readiness_is_current_but_not_scientific_certificate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, _, _ = build_ready_fixture(target)
            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--require-ready",
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "fixture-backend-1",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["contract_status"], "valid")
            self.assertEqual(report["currency_status"], "current")
            self.assertEqual(report["policy_status"], "conformant")
            self.assertTrue(report["declared_ready_and_current"])
            self.assertEqual(report["achieved_validation_level"], "sensitivity")
            spec = json.loads(
                (target / "analysis" / "specs" / "A-001.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(spec["target_validation_level"], "independent_external")
            self.assertEqual(
                report["scientific_validity"],
                "not_determined_by_contract_validator",
            )
            self.assertNotIn("usable", report)

    def test_blocked_readiness_authorizes_no_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["source_provenance_status"] = "conflicting"
            report["readiness_status"] = "blocked"
            report["claim_authorization"] = "not_authorized"
            report["authorized_claim_classes"] = []
            report["analysis_mode"] = "causal"
            report["requested_claim_class"] = "mechanism"
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["analysis_mode"] = "causal"
            spec["requested_claim_class"] = "mechanism"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["contract_status"], "valid")
            self.assertEqual(output["policy_status"], "conformant")
            self.assertEqual(output["computed_readiness"], "blocked")
            self.assertEqual(output["claim_authorization"], "not_authorized")
            self.assertFalse(output["declared_ready_and_current"])

    def test_verified_source_provenance_requires_identity_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            manifest_path = target / "provenance" / "SOURCE_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_context"]["source_reference"] = None
            write_json(manifest_path, manifest)
            report["input_manifest"]["sha256"] = sha256(manifest_path)
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["contract_status"], "invalid")
            self.assertIn(
                "readiness-source-provenance-incomplete",
                {item["code"] for item in output["findings"]},
            )

    def test_data_bearing_ready_requires_domain_spec_and_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for field in ("domain_spec", "domain_parameters"):
                with self.subTest(field=field):
                    target = Path(temporary) / field
                    report_path, report, _ = build_ready_fixture(target)
                    spec_path = target / "analysis" / "specs" / "A-001.json"
                    spec = json.loads(spec_path.read_text(encoding="utf-8"))
                    spec[field] = None if field == "domain_spec" else {}
                    write_json(spec_path, spec)
                    report["analysis_spec"]["sha256"] = sha256(spec_path)
                    report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
                    write_json(report_path, report)

                    result = validate_current_fixture(target, report_path)
                    self.assertEqual(result.returncode, 1)
                    codes = {
                        item["code"] for item in json.loads(result.stdout)["findings"]
                    }
                    self.assertIn(
                        f"analysis-spec-{field.replace('_', '-')}-required", codes
                    )

    def test_data_requirement_prevents_not_applicable_source_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["source_provenance_status"] = "not_applicable"
            report["input_manifest"] = None
            report["input_source_ids"] = []
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["input_source_ids"] = []
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            codes = {item["code"] for item in json.loads(result.stdout)["findings"]}
            self.assertIn("analysis-spec-source-required", codes)
            self.assertIn("analysis-spec-source-status-mismatch", codes)

    def test_data_free_contract_accepts_literal_none_enum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, policy = build_ready_fixture(target)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["data_requirement"] = "none"
            spec["input_source_ids"] = []
            spec["domain_spec"] = None
            spec["domain_parameters"] = {}
            write_json(spec_path, spec)
            report["source_provenance_status"] = "not_applicable"
            report["input_manifest"] = None
            report["input_source_ids"] = []
            report["achieved_validation_level"] = "none"
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            policy["applicable_data_requirements"] = ["none"]
            policy["authorizations"][0]["validation_levels"] = ["none"]
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)["declared_ready_and_current"])

    def test_policy_requires_declared_evidence_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, policy = build_ready_fixture(target)
            policy["gates"][0]["required_evidence_kinds"] = ["artifact"]
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["policy_status"], "nonconformant")
            self.assertIn(
                "policy-gate-evidence-kinds",
                {item["code"] for item in output["findings"]},
            )

    def test_placeholders_and_confirmatory_post_hoc_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "placeholders"
            report_path, report, policy = build_ready_fixture(target)
            policy["policy_id"] = "TODO"
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["estimand"] = "TBD"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            placeholder = validate_current_fixture(target, report_path)
            self.assertEqual(placeholder.returncode, 1)
            self.assertIn(
                "readiness-string",
                {item["code"] for item in json.loads(placeholder.stdout)["findings"]},
            )

            target = Path(temporary) / "confirmatory-post-hoc"
            report_path, report, policy = build_ready_fixture(target)
            report["analysis_mode"] = "confirmatory"
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["analysis_mode"] = "confirmatory"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            policy["authorizations"].append(
                {
                    "analysis_mode": "confirmatory",
                    "claim_classes": ["association"],
                    "validation_levels": ["sensitivity"],
                }
            )
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)
            post_hoc = validate_current_fixture(target, report_path)
            self.assertEqual(post_hoc.returncode, 1)
            self.assertIn(
                "analysis-spec-confirmatory-prespecification",
                {item["code"] for item in json.loads(post_hoc.stdout)["findings"]},
            )
            spec["prespecification"] = "not_applicable"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            not_applicable = validate_current_fixture(target, report_path)
            self.assertEqual(not_applicable.returncode, 1)
            self.assertIn(
                "analysis-spec-confirmatory-prespecification",
                {
                    item["code"]
                    for item in json.loads(not_applicable.stdout)["findings"]
                },
            )

            spec["prespecification"] = "prespecified_not_preregistered"
            spec["design"]["protocol_deviation_status"] = "unresolved"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            unresolved = validate_current_fixture(target, report_path)
            self.assertEqual(unresolved.returncode, 1)
            self.assertIn(
                "analysis-spec-unresolved-deviation",
                {item["code"] for item in json.loads(unresolved.stdout)["findings"]},
            )

    def test_spec_or_source_change_makes_readiness_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, _, _ = build_ready_fixture(target)
            (target / "analysis" / "specs" / "A-001.json").write_text(
                '{"analysis_id":"A-001","changed":true}\n', encoding="utf-8"
            )
            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--require-ready",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["contract_status"], "valid")
            self.assertEqual(report["currency_status"], "stale")
            self.assertFalse(report["declared_ready_and_current"])
            self.assertIn(
                "readiness-binding-stale",
                {item["code"] for item in report["findings"]},
            )

            report_path, report_document, _ = build_ready_fixture(
                Path(temporary) / "project-2"
            )
            second_target = report_path.parents[2]
            (second_target / "data" / "raw" / "input.tsv").write_text(
                "sample\tvalue\nS1\t99\n", encoding="utf-8"
            )
            source_changed = run_script(
                VALIDATE_READINESS,
                str(second_target),
                str(report_path.relative_to(second_target)),
                "--require-ready",
                "--json",
            )
            self.assertEqual(source_changed.returncode, 1)
            source_report = json.loads(source_changed.stdout)
            self.assertEqual(source_report["currency_status"], "stale")
            self.assertEqual(source_report["source_integrity_status"], "fail")
            self.assertTrue(report_document["input_source_ids"])

            report_path, _, _ = build_ready_fixture(Path(temporary) / "project-3")
            third_target = report_path.parents[2]
            (third_target / "scripts" / "python" / "analysis.py").write_text(
                "print('changed code')\n", encoding="utf-8"
            )
            code_changed = run_script(
                VALIDATE_READINESS,
                str(third_target),
                str(report_path.relative_to(third_target)),
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "fixture-backend-1",
                "--json",
            )
            self.assertEqual(code_changed.returncode, 1)
            code_report = json.loads(code_changed.stdout)
            self.assertEqual(code_report["currency_status"], "stale")
            self.assertEqual(code_report["code_integrity_status"], "fail")

    def test_weak_gate_and_unauthorized_claim_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["analysis_mode"] = "exploratory"
            report["requested_claim_class"] = "causal_effect"
            report["achieved_validation_level"] = "none"
            report["source_provenance_status"] = "conflicting"
            report["gates"][0]["evidence"] = []
            write_json(report_path, report)

            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--require-ready",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["contract_status"], "invalid")
            self.assertFalse(output["declared_ready_and_current"])
            codes = {item["code"] for item in output["findings"]}
            self.assertIn("readiness-gate-evidence", codes)
            self.assertIn("policy-authorization", codes)

    def test_evidence_is_typed_resolvable_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "assertion"
            report_path, report, _ = build_ready_fixture(target)
            report["gates"][0]["evidence"] = ["trust me"]
            write_json(report_path, report)
            assertion = validate_current_fixture(target, report_path)
            self.assertEqual(assertion.returncode, 1)
            assertion_output = json.loads(assertion.stdout)
            self.assertEqual(assertion_output["contract_status"], "invalid")
            self.assertIn(
                "readiness-evidence-item",
                {item["code"] for item in assertion_output["findings"]},
            )

            target = Path(temporary) / "file-drift"
            report_path, report, _ = build_ready_fixture(target)
            evidence_path = target / "docs" / "gate-evidence.txt"
            evidence_path.write_text("checked\n", encoding="utf-8")
            report["gates"][0]["evidence"] = [
                {
                    "kind": "file",
                    "ref": "docs/gate-evidence.txt",
                    "sha256": sha256(evidence_path),
                }
            ]
            write_json(report_path, report)
            current = validate_current_fixture(target, report_path)
            self.assertEqual(current.returncode, 0, current.stderr)
            evidence_path.write_text("changed\n", encoding="utf-8")
            drifted = validate_current_fixture(target, report_path)
            self.assertEqual(drifted.returncode, 1)
            drifted_output = json.loads(drifted.stdout)
            self.assertEqual(drifted_output["contract_status"], "valid")
            self.assertEqual(drifted_output["currency_status"], "stale")

            target = Path(temporary) / "bad-references"
            report_path, report, _ = build_ready_fixture(target)
            report["gates"][0]["evidence"] = [
                {"kind": "external", "ref": "data:text/plain,trust-me"},
                {"kind": "artifact", "ref": "ART-NOT-REGISTERED"},
            ]
            write_json(report_path, report)
            bad_references = validate_current_fixture(target, report_path)
            self.assertEqual(bad_references.returncode, 1)
            reference_codes = {
                item["code"] for item in json.loads(bad_references.stdout)["findings"]
            }
            self.assertIn("readiness-evidence-external", reference_codes)
            self.assertIn("readiness-evidence-registry-closure", reference_codes)

    def test_registry_evidence_closes_and_artifact_rebinding_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)

            artifact = target / "results" / "tables" / "gate-evidence.tsv"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("metric\tvalue\nqc\t1\n", encoding="utf-8")
            artifact_hash = sha256(artifact)
            artifact_registry = target / "provenance" / "ARTIFACTS.tsv"
            artifact_header = artifact_registry.read_text(
                encoding="utf-8"
            ).splitlines()[0]
            artifact_values = {
                "artifact_id": "ART-001",
                "analysis_id": "A-001",
                "path": "results/tables/gate-evidence.tsv",
                "role": "gate evidence",
                "source_provenance_status": "verified",
                "source_ids": report["input_source_ids"][0],
                "parent_artifact_ids": "ART-INPUT",
                "run_id": "RUN-001",
                "sha256": artifact_hash,
                "size_bytes": str(artifact.stat().st_size),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "access_class": "internal",
                "lifecycle_status": "current",
            }
            artifact_columns = artifact_header.split("\t")
            input_artifact = target / "data" / "raw" / "input.tsv"
            input_artifact_values = {
                "artifact_id": "ART-INPUT",
                "analysis_id": "A-001",
                "path": "data/raw/input.tsv",
                "role": "analysis input",
                "source_provenance_status": "verified",
                "source_ids": report["input_source_ids"][0],
                "sha256": sha256(input_artifact),
                "size_bytes": str(input_artifact.stat().st_size),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "access_class": "internal",
                "lifecycle_status": "current",
            }

            def write_artifacts() -> None:
                rows = (input_artifact_values, artifact_values)
                artifact_registry.write_text(
                    artifact_header
                    + "\n"
                    + "\n".join(
                        "\t".join(row.get(column, "") for column in artifact_columns)
                        for row in rows
                    )
                    + "\n",
                    encoding="utf-8",
                )

            write_artifacts()

            run_registry = target / "provenance" / "RUNS.tsv"
            run_header = run_registry.read_text(encoding="utf-8").splitlines()[0]
            run_log = target / "analysis" / "runs" / "RUN-001" / "run.log"
            run_log.parent.mkdir(parents=True)
            run_log.write_text("completed and validated\n", encoding="utf-8")
            completed_at = datetime.now(timezone.utc)
            run_values = {
                "run_id": "RUN-001",
                "analysis_id": "A-001",
                "implementation_status": "implemented",
                "execution_status": "completed",
                "technical_validation_status": "passed",
                "validation_kind": "output-integrity",
                "validation_scope": "A-001 complete fixture run",
                "validation_criterion": "expected output exists and checks pass",
                "validation_evidence_ids": "ART-001",
                "entry_point": "scripts/python/analysis.py",
                "config_path": "analysis/specs/A-001-domain.json",
                "config_sha256": sha256(
                    target / "analysis" / "specs" / "A-001-domain.json"
                ),
                "analysis_spec_path": "analysis/specs/A-001.json",
                "analysis_spec_sha256": sha256(
                    target / "analysis" / "specs" / "A-001.json"
                ),
                "input_artifact_ids": "ART-INPUT",
                "output_artifact_ids": "ART-001",
                "code_revision": "fixture-code-1",
                "code_dirty": "false",
                "backend_revision": "fixture-backend-1",
                "environment_ref": "provenance/ENVIRONMENT.lock",
                "started_at": (completed_at - timedelta(minutes=1)).isoformat(),
                "completed_at": completed_at.isoformat(),
                "exit_code": "0",
                "log_path": "analysis/runs/RUN-001/run.log",
            }
            run_columns = run_header.split("\t")
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )

            decision_log = target / "docs" / "DECISION_LOG.md"
            decision_section = (
                "### D-20260902-01 — Use registered QC evidence\n\n"
                "- Date: 2026-09-02\n"
                "- Analysis/claim/scope IDs: A-001\n"
                "- Decision: Use the registered QC result for gate assessment.\n"
                "- Evidence/source: ART-001 and RUN-001.\n"
                "- Reason: The recorded checks satisfy the fixture criterion.\n"
            )
            decision_log.write_text(
                decision_log.read_text(encoding="utf-8")
                + "\n"
                + decision_section,
                encoding="utf-8",
            )
            report["gates"][0]["evidence"] = [
                {
                    "kind": "file",
                    "ref": "analysis/specs/A-001.json",
                    "sha256": sha256(target / "analysis/specs/A-001.json"),
                },
                {
                    "kind": "artifact",
                    "ref": "ART-001",
                    "path": "results/tables/gate-evidence.tsv",
                    "sha256": artifact_hash,
                    "record_sha256": record_sha256(
                        {
                            column: artifact_values.get(column, "")
                            for column in artifact_columns
                        }
                    ),
                },
                {
                    "kind": "run",
                    "ref": "RUN-001",
                    "record_sha256": record_sha256(
                        {
                            column: run_values.get(column, "")
                            for column in run_columns
                        }
                    ),
                    "log_sha256": sha256(run_log),
                    "artifact_record_sha256s": {
                        "ART-INPUT": record_sha256(
                            {
                                column: input_artifact_values.get(column, "")
                                for column in artifact_columns
                            }
                        ),
                        "ART-001": record_sha256(
                            {
                                column: artifact_values.get(column, "")
                                for column in artifact_columns
                            }
                        ),
                    },
                },
                {
                    "kind": "decision",
                    "ref": "D-20260902-01",
                    "record_sha256": record_sha256(decision_section),
                },
                {"kind": "external", "ref": "https://doi.org/10.1000/fixture"},
                {"kind": "external", "ref": "URN:aa:x"},
            ]
            write_json(report_path, report)
            current = validate_current_fixture(target, report_path)
            self.assertEqual(current.returncode, 0, current.stderr)

            evidence_by_kind = {
                item["kind"]: item for item in report["gates"][0]["evidence"]
            }

            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["data_requirement"] = []
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            evidence_by_kind["file"]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            malformed_data_requirement = validate_current_fixture(target, report_path)
            self.assertEqual(malformed_data_requirement.returncode, 1)
            malformed_output = json.loads(malformed_data_requirement.stdout)
            self.assertIn(
                "analysis-spec-data-requirement",
                {item["code"] for item in malformed_output["findings"]},
            )
            spec["data_requirement"] = "data_bearing"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            evidence_by_kind["file"]["sha256"] = sha256(spec_path)
            write_json(report_path, report)

            run_log.write_text("validation failed after assessment\n", encoding="utf-8")
            changed_log = validate_current_fixture(target, report_path)
            self.assertEqual(changed_log.returncode, 1)
            self.assertIn(
                "readiness-evidence-run-log-stale",
                {item["code"] for item in json.loads(changed_log.stdout)["findings"]},
            )
            run_log.write_text("completed and validated\n", encoding="utf-8")

            original_gate_evidence = report["gates"][0]["evidence"]
            report["gates"][0]["evidence"] = [
                item for item in original_gate_evidence if item["kind"] != "artifact"
            ]
            rebound_artifact = target / "results" / "tables" / "rebound.tsv"
            rebound_artifact.write_text("metric\tvalue\nqc\t999\n", encoding="utf-8")
            original_artifact_binding = {
                key: artifact_values[key] for key in ("path", "sha256", "size_bytes")
            }
            artifact_values["path"] = "results/tables/rebound.tsv"
            artifact_values["sha256"] = sha256(rebound_artifact)
            artifact_values["size_bytes"] = str(rebound_artifact.stat().st_size)
            write_artifacts()
            write_json(report_path, report)
            transitive_rebind = validate_current_fixture(target, report_path)
            self.assertEqual(transitive_rebind.returncode, 1)
            self.assertIn(
                "readiness-evidence-run-artifact-record-stale",
                {
                    item["code"]
                    for item in json.loads(transitive_rebind.stdout)["findings"]
                },
            )
            artifact_values.update(original_artifact_binding)
            write_artifacts()
            report["gates"][0]["evidence"] = original_gate_evidence
            write_json(report_path, report)

            input_artifact_values["source_ids"] = ""
            write_artifacts()
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-INPUT"] = (
                record_sha256(
                    {
                        column: input_artifact_values.get(column, "")
                        for column in artifact_columns
                    }
                )
            )
            write_json(report_path, report)

            original_config_hash = run_values["config_sha256"]
            run_values["config_sha256"] = ""
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )
            evidence_by_kind["run"]["record_sha256"] = record_sha256(
                {column: run_values.get(column, "") for column in run_columns}
            )
            write_json(report_path, report)
            unbound_config = validate_current_fixture(target, report_path)
            self.assertEqual(unbound_config.returncode, 1)
            self.assertIn(
                "readiness-binding-sha256",
                {item["code"] for item in json.loads(unbound_config.stdout)["findings"]},
            )
            run_values["config_sha256"] = original_config_hash
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )
            evidence_by_kind["run"]["record_sha256"] = record_sha256(
                {column: run_values.get(column, "") for column in run_columns}
            )
            write_json(report_path, report)

            artifact_values["parent_artifact_ids"] = "ART-NOT-AN-INPUT"
            write_artifacts()
            artifact_row_digest = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            evidence_by_kind["artifact"]["record_sha256"] = artifact_row_digest
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-001"] = (
                artifact_row_digest
            )
            write_json(report_path, report)
            detached_parent = validate_current_fixture(target, report_path)
            self.assertEqual(detached_parent.returncode, 1)
            self.assertIn(
                "readiness-evidence-run-parent-lineage",
                {item["code"] for item in json.loads(detached_parent.stdout)["findings"]},
            )
            artifact_values["parent_artifact_ids"] = "ART-INPUT"
            write_artifacts()
            artifact_row_digest = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            evidence_by_kind["artifact"]["record_sha256"] = artifact_row_digest
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-001"] = (
                artifact_row_digest
            )

            original_artifact_binding = {
                key: artifact_values[key] for key in ("path", "sha256", "size_bytes")
            }
            artifact_values["path"] = input_artifact_values["path"]
            artifact_values["sha256"] = input_artifact_values["sha256"]
            artifact_values["size_bytes"] = input_artifact_values["size_bytes"]
            write_artifacts()
            artifact_row_digest = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            evidence_by_kind["artifact"].update(
                {
                    "path": artifact_values["path"],
                    "sha256": artifact_values["sha256"],
                    "record_sha256": artifact_row_digest,
                }
            )
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-001"] = (
                artifact_row_digest
            )
            write_json(report_path, report)
            overlapping_path = validate_current_fixture(target, report_path)
            self.assertEqual(overlapping_path.returncode, 1)
            self.assertIn(
                "readiness-evidence-run-path-overlap",
                {item["code"] for item in json.loads(overlapping_path.stdout)["findings"]},
            )
            artifact_values.update(original_artifact_binding)
            write_artifacts()
            artifact_row_digest = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            evidence_by_kind["artifact"].update(
                {
                    "path": artifact_values["path"],
                    "sha256": artifact_values["sha256"],
                    "record_sha256": artifact_row_digest,
                }
            )
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-001"] = (
                artifact_row_digest
            )
            write_json(report_path, report)
            detached_source = validate_current_fixture(target, report_path)
            self.assertEqual(detached_source.returncode, 1)
            detached_codes = {
                item["code"] for item in json.loads(detached_source.stdout)["findings"]
            }
            self.assertIn("readiness-artifact-source-ids", detached_codes)
            self.assertIn("readiness-evidence-run-source-lineage", detached_codes)
            input_artifact_values["source_ids"] = report["input_source_ids"][0]
            write_artifacts()
            evidence_by_kind["run"]["artifact_record_sha256s"]["ART-INPUT"] = (
                record_sha256(
                    {
                        column: input_artifact_values.get(column, "")
                        for column in artifact_columns
                    }
                )
            )
            write_json(report_path, report)

            artifact_values["role"] = ""
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            write_json(report_path, report)
            incomplete_artifact = validate_current_fixture(target, report_path)
            self.assertEqual(incomplete_artifact.returncode, 1)
            self.assertIn(
                "readiness-artifact-row-incomplete",
                {
                    item["code"]
                    for item in json.loads(incomplete_artifact.stdout)["findings"]
                },
            )
            artifact_values["role"] = "gate evidence"
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )

            artifact_values["source_provenance_status"] = "not_applicable"
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            write_json(report_path, report)
            disconnected_provenance = validate_current_fixture(target, report_path)
            self.assertEqual(disconnected_provenance.returncode, 1)
            self.assertIn(
                "readiness-artifact-source-provenance",
                {
                    item["code"]
                    for item in json.loads(disconnected_provenance.stdout)["findings"]
                },
            )
            artifact_values["source_provenance_status"] = "verified"
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )

            original_size = artifact_values["size_bytes"]
            artifact_values["size_bytes"] = str(int(original_size) + 1)
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )
            write_json(report_path, report)
            wrong_size = validate_current_fixture(target, report_path)
            self.assertEqual(wrong_size.returncode, 1)
            self.assertIn(
                "readiness-artifact-size-stale",
                {item["code"] for item in json.loads(wrong_size.stdout)["findings"]},
            )
            artifact_values["size_bytes"] = original_size
            write_artifacts()
            evidence_by_kind["artifact"]["record_sha256"] = record_sha256(
                {
                    column: artifact_values.get(column, "")
                    for column in artifact_columns
                }
            )

            original_output_ids = run_values["output_artifact_ids"]
            original_log_path = run_values["log_path"]
            run_values["output_artifact_ids"] = "ART-NOT-REGISTERED"
            run_values["log_path"] = "analysis/runs/RUN-001/missing.log"
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )
            evidence_by_kind["run"]["record_sha256"] = record_sha256(
                {column: run_values.get(column, "") for column in run_columns}
            )
            write_json(report_path, report)
            open_run_lineage = validate_current_fixture(target, report_path)
            self.assertEqual(open_run_lineage.returncode, 1)
            open_run_codes = {
                item["code"] for item in json.loads(open_run_lineage.stdout)["findings"]
            }
            self.assertIn("readiness-evidence-registry-closure", open_run_codes)
            self.assertIn("readiness-evidence-run-log", open_run_codes)
            run_values["output_artifact_ids"] = original_output_ids
            run_values["log_path"] = original_log_path
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )
            evidence_by_kind["run"]["record_sha256"] = record_sha256(
                {column: run_values.get(column, "") for column in run_columns}
            )

            decision_log.write_text(
                decision_log.read_text(encoding="utf-8").replace(
                    "- Reason: The recorded checks satisfy the fixture criterion.\n",
                    "",
                ),
                encoding="utf-8",
            )
            incomplete_decision_section = decision_section.replace(
                "- Reason: The recorded checks satisfy the fixture criterion.\n",
                "",
            )
            evidence_by_kind["decision"]["record_sha256"] = record_sha256(
                incomplete_decision_section
            )
            write_json(report_path, report)
            incomplete_decision = validate_current_fixture(target, report_path)
            self.assertEqual(incomplete_decision.returncode, 1)
            self.assertIn(
                "readiness-evidence-decision-closure",
                {
                    item["code"]
                    for item in json.loads(incomplete_decision.stdout)["findings"]
                },
            )
            decision_log.write_text(
                decision_log.read_text(encoding="utf-8")
                + "- Reason: The recorded checks satisfy the fixture criterion.\n",
                encoding="utf-8",
            )
            evidence_by_kind["decision"]["record_sha256"] = record_sha256(
                decision_section
            )
            write_json(report_path, report)

            duplicate_reason_section = (
                decision_section + "- Reason: A second conflicting rationale.\n"
            )
            decision_log.write_text(
                decision_log.read_text(encoding="utf-8").replace(
                    decision_section, duplicate_reason_section
                ),
                encoding="utf-8",
            )
            evidence_by_kind["decision"]["record_sha256"] = record_sha256(
                duplicate_reason_section
            )
            write_json(report_path, report)
            duplicate_decision_field = validate_current_fixture(target, report_path)
            self.assertEqual(duplicate_decision_field.returncode, 1)
            self.assertIn(
                "readiness-evidence-decision-closure",
                {
                    item["code"]
                    for item in json.loads(duplicate_decision_field.stdout)["findings"]
                },
            )
            decision_log.write_text(
                decision_log.read_text(encoding="utf-8").replace(
                    duplicate_reason_section, decision_section
                ),
                encoding="utf-8",
            )
            evidence_by_kind["decision"]["record_sha256"] = record_sha256(
                decision_section
            )
            write_json(report_path, report)

            artifact_values["analysis_id"] = "A-OTHER"
            write_artifacts()
            cross_analysis = validate_current_fixture(target, report_path)
            self.assertEqual(cross_analysis.returncode, 1)
            self.assertIn(
                "readiness-evidence-artifact-analysis",
                {
                    item["code"]
                    for item in json.loads(cross_analysis.stdout)["findings"]
                },
            )
            artifact_values["analysis_id"] = "A-001"
            write_artifacts()

            decision_log.write_text(
                decision_log.read_text(encoding="utf-8").replace(
                    "- Analysis/claim/scope IDs: A-001",
                    "- Analysis/claim/scope IDs: A-OTHER",
                ),
                encoding="utf-8",
            )
            wrong_decision_scope = validate_current_fixture(target, report_path)
            self.assertEqual(wrong_decision_scope.returncode, 1)
            self.assertIn(
                "readiness-evidence-decision-closure",
                {
                    item["code"]
                    for item in json.loads(wrong_decision_scope.stdout)["findings"]
                },
            )
            decision_log.write_text(
                decision_log.read_text(encoding="utf-8").replace(
                    "- Analysis/claim/scope IDs: A-OTHER",
                    "- Analysis/claim/scope IDs: A-001",
                ),
                encoding="utf-8",
            )

            artifact_values["lifecycle_status"] = "invalidated"
            write_artifacts()
            invalidated = validate_current_fixture(target, report_path)
            self.assertEqual(invalidated.returncode, 1)
            invalidated_output = json.loads(invalidated.stdout)
            self.assertEqual(invalidated_output["currency_status"], "stale")
            self.assertIn(
                "readiness-evidence-artifact-lifecycle",
                {item["code"] for item in invalidated_output["findings"]},
            )
            artifact_values["lifecycle_status"] = "current"
            write_artifacts()

            run_values["execution_status"] = "failed"
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )
            failed_run = validate_current_fixture(target, report_path)
            self.assertEqual(failed_run.returncode, 1)
            failed_run_output = json.loads(failed_run.stdout)
            self.assertEqual(failed_run_output["currency_status"], "stale")
            self.assertIn(
                "readiness-evidence-run-execution",
                {item["code"] for item in failed_run_output["findings"]},
            )
            run_values["execution_status"] = "completed"
            run_registry.write_text(
                run_header
                + "\n"
                + "\t".join(run_values.get(column, "") for column in run_columns)
                + "\n",
                encoding="utf-8",
            )

            artifact.write_text("metric\tvalue\nqc\t2\n", encoding="utf-8")
            artifact_values["sha256"] = sha256(artifact)
            artifact_values["size_bytes"] = str(artifact.stat().st_size)
            write_artifacts()
            rebound = validate_current_fixture(target, report_path)
            self.assertEqual(rebound.returncode, 1)
            rebound_output = json.loads(rebound.stdout)
            self.assertEqual(rebound_output["contract_status"], "invalid")
            self.assertIn(
                "readiness-evidence-artifact-mismatch",
                {item["code"] for item in rebound_output["findings"]},
            )

    def test_malformed_enums_remain_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["analysis_mode"] = []
            report["gates"][0]["status"] = []
            report["gates"][0]["evidence"] = [{"kind": [], "ref": "x"}]
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            codes = {item["code"] for item in output["findings"]}
            self.assertIn("readiness-analysis-mode", codes)
            self.assertIn("readiness-gate-status", codes)
            self.assertIn("readiness-evidence-kind", codes)

    def test_scalar_evidence_and_mutable_external_url_fail_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "scalar"
            report_path, report, _ = build_ready_fixture(target)
            report["gates"][0]["evidence"] = None
            write_json(report_path, report)
            scalar = validate_current_fixture(target, report_path)
            self.assertEqual(scalar.returncode, 1)
            scalar_output = json.loads(scalar.stdout)
            self.assertIn(
                "readiness-evidence-list",
                {item["code"] for item in scalar_output["findings"]},
            )

            target = Path(temporary) / "mutable-url"
            report_path, report, _ = build_ready_fixture(target)
            base_evidence = list(report["gates"][0]["evidence"])
            invalid_external_refs = [
                "https://example.com/mutable",
                "urn:a:x",
                "urn:a-:xx",
                "urn:aa:%ZZ",
                "urn:aa:%00",
                "urn:aa:x<y",
                "urn:aa:x\\y",
                "urn:aa:x\x00y",
                "urn:aa:x?+",
                "https://doi.org:443/10.1000/fixture",
                "https://doi.org/10.1000/fixture?mutable=1",
                "https://doi.org/10.1000/fixture#fragment",
                "https://doi.org/10.1000/%ZZ",
                "https://doi.org/10.1000/%00",
                "https://doi.org/10.1000/x<y",
                "https://DOI.ORG/10.1000/fixture",
            ]
            for reference in invalid_external_refs:
                with self.subTest(reference=repr(reference)):
                    report["gates"][0]["evidence"] = base_evidence + [
                        {"kind": "external", "ref": reference}
                    ]
                    write_json(report_path, report)
                    mutable = validate_current_fixture(target, report_path)
                    self.assertEqual(mutable.returncode, 1)
                    self.assertIn(
                        "readiness-evidence-external",
                        {
                            item["code"]
                            for item in json.loads(mutable.stdout)["findings"]
                        },
                    )

            target = Path(temporary) / "wide-registry-row"
            report_path, report, _ = build_ready_fixture(target)
            registry = target / "provenance" / "ARTIFACTS.tsv"
            header = registry.read_text(encoding="utf-8").splitlines()[0]
            registry.write_text(
                header + "\n" + "\t".join(["ART-X"] + [""] * len(header.split("\t"))) + "\n",
                encoding="utf-8",
            )
            report["gates"][0]["evidence"].append(
                {
                    "kind": "artifact",
                    "ref": "ART-X",
                    "path": "results/tables/x.tsv",
                    "sha256": "0" * 64,
                    "record_sha256": "0" * 64,
                }
            )
            write_json(report_path, report)
            malformed_registry = validate_current_fixture(target, report_path)
            self.assertEqual(malformed_registry.returncode, 1)
            malformed_output = json.loads(malformed_registry.stdout)
            self.assertIn(
                "readiness-evidence-registry",
                {item["code"] for item in malformed_output["findings"]},
            )

    def test_run_evidence_binds_analysis_and_passed_technical_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            input_artifact = target / "data" / "raw" / "input.tsv"
            output_artifact = target / "results" / "tables" / "run-output.tsv"
            output_artifact.parent.mkdir(parents=True, exist_ok=True)
            output_artifact.write_text("metric\tvalue\nresult\t1\n", encoding="utf-8")
            artifact_registry = target / "provenance" / "ARTIFACTS.tsv"
            artifact_header = artifact_registry.read_text(
                encoding="utf-8"
            ).splitlines()[0]
            artifact_columns = artifact_header.split("\t")
            artifact_rows = (
                {
                    "artifact_id": "ART-INPUT",
                    "analysis_id": "A-001",
                    "path": "data/raw/input.tsv",
                    "role": "analysis input",
                    "source_provenance_status": "verified",
                    "source_ids": report["input_source_ids"][0],
                    "sha256": sha256(input_artifact),
                    "size_bytes": str(input_artifact.stat().st_size),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "access_class": "internal",
                    "lifecycle_status": "current",
                },
                {
                    "artifact_id": "ART-001",
                    "analysis_id": "A-001",
                    "path": "results/tables/run-output.tsv",
                    "role": "validated run output",
                    "source_provenance_status": "verified",
                    "source_ids": report["input_source_ids"][0],
                    "parent_artifact_ids": "ART-INPUT",
                    "run_id": "RUN-OTHER",
                    "sha256": sha256(output_artifact),
                    "size_bytes": str(output_artifact.stat().st_size),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "access_class": "internal",
                    "lifecycle_status": "current",
                },
            )
            artifact_registry.write_text(
                artifact_header
                + "\n"
                + "\n".join(
                    "\t".join(row.get(column, "") for column in artifact_columns)
                    for row in artifact_rows
                )
                + "\n",
                encoding="utf-8",
            )
            run_registry = target / "provenance" / "RUNS.tsv"
            header = run_registry.read_text(encoding="utf-8").splitlines()[0]
            columns = header.split("\t")
            run_log = target / "analysis" / "runs" / "RUN-OTHER" / "run.log"
            run_log.parent.mkdir(parents=True)
            run_log.write_text("completed and validated\n", encoding="utf-8")
            completed_at = datetime.now(timezone.utc)
            values = {
                "run_id": "RUN-OTHER",
                "analysis_id": "A-OTHER",
                "implementation_status": "implemented",
                "execution_status": "completed",
                "technical_validation_status": "passed",
                "validation_kind": "output-integrity",
                "validation_scope": "A-001 complete fixture run",
                "validation_criterion": "expected output exists and checks pass",
                "validation_evidence_ids": "ART-001",
                "entry_point": "scripts/python/analysis.py",
                "config_path": "analysis/specs/A-001-domain.json",
                "config_sha256": sha256(
                    target / "analysis" / "specs" / "A-001-domain.json"
                ),
                "analysis_spec_path": "analysis/specs/A-001.json",
                "analysis_spec_sha256": sha256(
                    target / "analysis" / "specs" / "A-001.json"
                ),
                "input_artifact_ids": "ART-INPUT",
                "output_artifact_ids": "ART-001",
                "code_revision": "fixture-code-1",
                "code_dirty": "false",
                "backend_revision": "fixture-backend-1",
                "environment_ref": "provenance/ENVIRONMENT.lock",
                "started_at": (completed_at - timedelta(minutes=1)).isoformat(),
                "completed_at": completed_at.isoformat(),
                "exit_code": "0",
                "log_path": "analysis/runs/RUN-OTHER/run.log",
            }

            def write_run() -> None:
                run_registry.write_text(
                    header
                    + "\n"
                    + "\t".join(values.get(column, "") for column in columns)
                    + "\n",
                    encoding="utf-8",
                )

            write_run()
            report["gates"][0]["evidence"].append(
                {
                    "kind": "run",
                    "ref": "RUN-OTHER",
                    "record_sha256": record_sha256(
                        {column: values.get(column, "") for column in columns}
                    ),
                    "log_sha256": sha256(run_log),
                    "artifact_record_sha256s": {
                        row["artifact_id"]: record_sha256(
                            {
                                column: row.get(column, "")
                                for column in artifact_columns
                            }
                        )
                        for row in artifact_rows
                    },
                }
            )
            write_json(report_path, report)
            wrong_analysis = validate_current_fixture(target, report_path)
            self.assertEqual(wrong_analysis.returncode, 1)
            self.assertIn(
                "readiness-evidence-run-analysis",
                {
                    item["code"]
                    for item in json.loads(wrong_analysis.stdout)["findings"]
                },
            )

            values["analysis_id"] = "A-001"
            values["technical_validation_status"] = "failed"
            write_run()
            failed_validation = validate_current_fixture(target, report_path)
            self.assertEqual(failed_validation.returncode, 1)
            failed_output = json.loads(failed_validation.stdout)
            self.assertEqual(failed_output["currency_status"], "stale")
            self.assertIn(
                "readiness-evidence-run-validation",
                {item["code"] for item in failed_output["findings"]},
            )

    def test_authorized_claim_classes_require_policy_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["authorized_claim_classes"].append("mechanism")
            report["prohibited_claim_classes"].remove("mechanism")
            write_json(report_path, report)

            result = validate_current_fixture(target, report_path)
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["policy_status"], "nonconformant")
            self.assertIn(
                "policy-allowed-claim-classes",
                {item["code"] for item in output["findings"]},
            )

    def test_na_cannot_bypass_gate_when_policy_disallows_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["gates"][0]["status"] = "NA"
            report["gates"][0]["evidence"] = [
                {
                    "kind": "file",
                    "ref": "analysis/specs/A-001.json",
                    "sha256": sha256(target / "analysis" / "specs" / "A-001.json"),
                }
            ]
            write_json(report_path, report)

            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--require-ready",
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "fixture-backend-1",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["policy_status"], "nonconformant")
            self.assertIn(
                "policy-gate-na-not-allowed",
                {item["code"] for item in output["findings"]},
            )

    def test_invalid_gate_policy_is_nonconformant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, policy = build_ready_fixture(target)
            policy["authorizations"].append(dict(policy["authorizations"][0]))
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)

            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "fixture-backend-1",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["contract_status"], "invalid")
            self.assertEqual(output["policy_status"], "nonconformant")

    def test_malformed_policy_remains_machine_readable(self) -> None:
        cases: list[tuple[str, tuple[str | int, ...], object]] = [
            ("claim-classes", ("authorizations", 0, "claim_classes"), 1),
            ("validation-levels", ("authorizations", 0, "validation_levels"), 1),
            ("authorizations", ("authorizations",), 1),
            ("assessor", ("assessor",), []),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            for name, path, malformed_value in cases:
                with self.subTest(name=name):
                    target = Path(temporary) / name
                    report_path, report, policy = build_ready_fixture(target)
                    cursor: object = policy
                    for part in path[:-1]:
                        cursor = cursor[part]  # type: ignore[index]
                    cursor[path[-1]] = malformed_value  # type: ignore[index]
                    policy_path = (
                        target / "analysis" / "specs" / "fixture-gate-policy.json"
                    )
                    write_json(policy_path, policy)
                    report["gate_policy"]["sha256"] = sha256(policy_path)
                    write_json(report_path, report)

                    result = validate_current_fixture(target, report_path)
                    self.assertEqual(result.returncode, 1)
                    output = json.loads(result.stdout)
                    self.assertEqual(output["contract_status"], "invalid")
                    self.assertEqual(output["policy_status"], "nonconformant")

    def test_readiness_and_analysis_spec_must_have_semantic_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["analysis_id"] = "A-DIFFERENT"
            spec["input_source_ids"] = []
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            write_json(report_path, report)

            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "fixture-backend-1",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            codes = {item["code"] for item in output["findings"]}
            self.assertIn("analysis-spec-mismatch", codes)
            self.assertIn("analysis-spec-source-ids", codes)

    def test_analysis_units_close_against_ordered_unit_hierarchy(self) -> None:
        cases = (
            (
                "missing-independent-unit",
                ["sample"],
                "analysis-spec-unit-hierarchy-closure",
            ),
            (
                "reversed-nesting",
                ["sample", "subject"],
                "analysis-spec-unit-hierarchy-order",
            ),
            (
                "level-above-independent-unit",
                ["cohort", "subject", "sample"],
                "analysis-spec-unit-hierarchy-order",
            ),
            (
                "level-below-observation-unit",
                ["subject", "sample", "feature"],
                "analysis-spec-unit-hierarchy-order",
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            for name, hierarchy, expected_code in cases:
                with self.subTest(name=name):
                    target = Path(temporary) / name
                    report_path, report, _ = build_ready_fixture(target)
                    spec_path = target / "analysis" / "specs" / "A-001.json"
                    spec = json.loads(spec_path.read_text(encoding="utf-8"))
                    spec["design"]["unit_hierarchy"] = hierarchy
                    write_json(spec_path, spec)
                    report["analysis_spec"]["sha256"] = sha256(spec_path)
                    report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
                    write_json(report_path, report)

                    result = validate_current_fixture(target, report_path)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(
                        expected_code,
                        {
                            item["code"]
                            for item in json.loads(result.stdout)["findings"]
                        },
                    )

    def test_gate_policy_domain_and_study_type_must_apply_to_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "domain"
            report_path, report, policy = build_ready_fixture(target)
            policy["domain"] = "unrelated-clinical-imaging-domain"
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)
            domain = validate_current_fixture(target, report_path)
            self.assertEqual(domain.returncode, 1)
            self.assertIn(
                "policy-domain-mismatch",
                {item["code"] for item in json.loads(domain.stdout)["findings"]},
            )

            target = Path(temporary) / "study-type"
            report_path, report, _ = build_ready_fixture(target)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["study_type"] = "randomized-device-trial"
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            study_type = validate_current_fixture(target, report_path)
            self.assertEqual(study_type.returncode, 1)
            study_output = json.loads(study_type.stdout)
            self.assertEqual(study_output["policy_status"], "nonconformant")
            self.assertIn(
                "policy-study-type-not-applicable",
                {item["code"] for item in study_output["findings"]},
            )

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "duplicate"
            report_path, _, _ = build_ready_fixture(target)
            raw_report = report_path.read_text(encoding="utf-8")
            raw_report = raw_report.replace(
                '  "readiness_status": "ready",',
                '  "readiness_status": "blocked",\n  "readiness_status": "ready",',
                1,
            )
            report_path.write_text(raw_report, encoding="utf-8")
            duplicate = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--json",
            )
            self.assertEqual(duplicate.returncode, 2)
            duplicate_output = json.loads(duplicate.stdout)
            self.assertEqual(duplicate_output["status"], "error")
            self.assertIn("Duplicate JSON object key", duplicate_output["error"])

            target = Path(temporary) / "nonfinite"
            report_path, report, _ = build_ready_fixture(target)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["domain_parameters"]["comparison"] = float("nan")
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            nonfinite = validate_current_fixture(target, report_path)
            self.assertEqual(nonfinite.returncode, 1)
            self.assertIn(
                "analysis-spec-read",
                {item["code"] for item in json.loads(nonfinite.stdout)["findings"]},
            )

    def test_json_edge_cases_fail_without_tracebacks(self) -> None:
        malformed_documents = {
            "lone-surrogate": '{"x":"\\ud800"}',
            "deep-nesting": '{"x":' + "[" * 1500 + "0" + "]" * 1500 + "}",
            "float-overflow": '{"x":1e9999}',
            "huge-integer": '{"x":' + "9" * 5000 + "}",
        }
        with tempfile.TemporaryDirectory() as temporary:
            for name, content in malformed_documents.items():
                with self.subTest(name=name):
                    target = Path(temporary) / name
                    report_path = target / "analysis" / "readiness" / "bad.json"
                    report_path.parent.mkdir(parents=True)
                    report_path.write_text(content, encoding="utf-8")
                    result = run_script(
                        VALIDATE_READINESS,
                        str(target),
                        str(report_path.relative_to(target)),
                        "--json",
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIsInstance(json.loads(result.stdout), dict)
                    self.assertNotIn("Traceback", result.stderr)

    def test_backend_environment_and_code_entry_points_are_concrete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "backend"
            report_path, report, _ = build_ready_fixture(target)
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["backend_revision"] = "TODO"
            write_json(spec_path, spec)
            report["backend_revision"] = "TODO"
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            backend = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--current-code-revision",
                "fixture-code-1",
                "--current-code-dirty",
                "false",
                "--current-backend-revision",
                "TODO",
                "--json",
            )
            self.assertEqual(backend.returncode, 1)
            self.assertIn(
                "readiness-backend-revision",
                {item["code"] for item in json.loads(backend.stdout)["findings"]},
            )

            target = Path(temporary) / "environment"
            report_path, report, _ = build_ready_fixture(target)
            environment = target / "provenance" / "ENVIRONMENT.lock"
            for content, expected_code in (
                (b" \n\t", "readiness-environment-empty"),
                (b"TODO\n", "readiness-environment-placeholder"),
            ):
                with self.subTest(environment_content=content):
                    environment.write_bytes(content)
                    report["environment_snapshot"]["sha256"] = sha256(environment)
                    write_json(report_path, report)
                    invalid_environment = validate_current_fixture(
                        target, report_path
                    )
                    self.assertEqual(invalid_environment.returncode, 1)
                    self.assertIn(
                        expected_code,
                        {
                            item["code"]
                            for item in json.loads(invalid_environment.stdout)[
                                "findings"
                            ]
                        },
                    )

            target = Path(temporary) / "entry-point"
            report_path, report, _ = build_ready_fixture(target)
            unrelated = run_script(
                BUILD_SOURCE,
                str(target),
                "--include",
                "docs",
                "--output",
                "provenance/UNRELATED_CODE_MANIFEST.json",
                "--source-system",
                "local-project-code",
                "--apply",
                "--json",
            )
            self.assertEqual(unrelated.returncode, 0, unrelated.stderr)
            unrelated_path = target / "provenance" / "UNRELATED_CODE_MANIFEST.json"
            report["code_manifest"] = {
                "path": "provenance/UNRELATED_CODE_MANIFEST.json",
                "sha256": sha256(unrelated_path),
            }
            write_json(report_path, report)
            uncovered = validate_current_fixture(target, report_path)
            self.assertEqual(uncovered.returncode, 1)
            self.assertIn(
                "code-manifest-entry-points-missing",
                {item["code"] for item in json.loads(uncovered.stdout)["findings"]},
            )

    def test_assessor_version_and_readiness_id_are_unique_and_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "assessor"
            report_path, report, policy = build_ready_fixture(target)
            policy["assessor"]["version"] = "2.0.0"
            policy_path = target / "analysis" / "specs" / "fixture-gate-policy.json"
            write_json(policy_path, policy)
            report["gate_policy"]["sha256"] = sha256(policy_path)
            write_json(report_path, report)
            mismatch = validate_current_fixture(target, report_path)
            self.assertEqual(mismatch.returncode, 1)
            self.assertIn(
                "policy-assessor-version-mismatch",
                {item["code"] for item in json.loads(mismatch.stdout)["findings"]},
            )

            target = Path(temporary) / "duplicate-id"
            report_path, report, _ = build_ready_fixture(target)
            write_json(
                target / "analysis" / "readiness" / "duplicate.json",
                report,
            )
            duplicate = validate_current_fixture(target, report_path)
            self.assertEqual(duplicate.returncode, 1)
            self.assertIn(
                "readiness-id-duplicate",
                {item["code"] for item in json.loads(duplicate.stdout)["findings"]},
            )

    def test_readiness_runtime_rejects_extra_fields_bool_as_int_and_bad_source_id(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            report["unexpected"] = "not in schema"
            report["code_dirty"] = 0
            report["input_source_ids"] = ["SRC-NOT-IN-MANIFEST"]
            write_json(report_path, report)

            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            codes = {item["code"] for item in output["findings"]}
            self.assertIn("readiness-property", codes)
            self.assertIn("readiness-code-dirty", codes)
            self.assertIn("readiness-source-id", codes)

    def test_revision_mismatch_and_expiry_are_stale_future_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, report, _ = build_ready_fixture(target)
            write_json(report_path, report)
            stale = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--max-age-days",
                "0",
                "--current-code-revision",
                "different-code",
                "--json",
            )
            self.assertEqual(stale.returncode, 1)
            stale_report = json.loads(stale.stdout)
            self.assertEqual(stale_report["contract_status"], "valid")
            self.assertEqual(stale_report["currency_status"], "stale")
            stale_codes = {item["code"] for item in stale_report["findings"]}
            self.assertIn("readiness-expired", stale_codes)
            self.assertIn("readiness-code-revision-stale", stale_codes)

            report["assessed_at"] = (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat()
            write_json(report_path, report)
            future = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--json",
            )
            self.assertEqual(future.returncode, 1)
            future_report = json.loads(future.stdout)
            self.assertEqual(future_report["contract_status"], "invalid")
            self.assertIn(
                "readiness-future",
                {item["code"] for item in future_report["findings"]},
            )

    def test_manifest_and_spec_timestamps_close_before_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "source-order"
            (target / "data" / "raw").mkdir(parents=True)
            (target / "data" / "raw" / "input.txt").write_text("x\n", encoding="utf-8")
            built = run_script(BUILD_SOURCE, str(target), "--apply", "--json")
            self.assertEqual(built.returncode, 0, built.stderr)
            manifest_path = target / "provenance" / "SOURCE_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["generated_at"] = (
                datetime.now(timezone.utc) - timedelta(days=2)
            ).isoformat()
            manifest["source_context"]["acquired_at"] = (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).isoformat()
            write_json(manifest_path, manifest)
            reversed_time = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(reversed_time.returncode, 1)
            self.assertIn(
                "source-time-order",
                {item["code"] for item in json.loads(reversed_time.stdout)["findings"]},
            )
            manifest["generated_at"] = "2099-01-02T00:00:00Z"
            manifest["source_context"]["acquired_at"] = "2099-01-01T00:00:00Z"
            write_json(manifest_path, manifest)
            future_source = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(future_source.returncode, 1)
            future_codes = {
                item["code"] for item in json.loads(future_source.stdout)["findings"]
            }
            self.assertIn("source-generated-at-future", future_codes)
            self.assertIn("source-acquired-at-future", future_codes)
            manifest["generated_at"] = "2026-09-03 00:00:00+00:00"
            manifest["source_context"]["acquired_at"] = None
            write_json(manifest_path, manifest)
            non_rfc3339 = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(non_rfc3339.returncode, 1)
            self.assertIn(
                "source-generated-at",
                {
                    item["code"]
                    for item in json.loads(non_rfc3339.stdout)["findings"]
                },
            )

            target = Path(temporary) / "spec-after-assessment"
            report_path, report, _ = build_ready_fixture(target)
            assessed_at = datetime.fromisoformat(report["assessed_at"])
            spec_path = target / "analysis" / "specs" / "A-001.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["created_at"] = (assessed_at + timedelta(hours=1)).isoformat()
            write_json(spec_path, spec)
            report["analysis_spec"]["sha256"] = sha256(spec_path)
            report["gates"][0]["evidence"][0]["sha256"] = sha256(spec_path)
            write_json(report_path, report)
            after_assessment = validate_current_fixture(target, report_path)
            self.assertEqual(after_assessment.returncode, 1)
            self.assertIn(
                "analysis-spec-after-assessment",
                {
                    item["code"]
                    for item in json.loads(after_assessment.stdout)["findings"]
                },
            )

    def test_unchecked_revisions_make_currency_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            report_path, _, _ = build_ready_fixture(target)
            result = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report_path.relative_to(target)),
                "--require-ready",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertEqual(output["contract_status"], "valid")
            self.assertEqual(output["currency_status"], "unknown")
            self.assertFalse(output["declared_ready_and_current"])

    def test_cli_scripts_are_executable(self) -> None:
        for script in (AUDIT, BUILD_SOURCE, VERIFY_SOURCE, VALIDATE_READINESS):
            self.assertTrue(os.access(script, os.X_OK), script)

    def test_json_mode_keeps_post_parse_errors_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / "provenance").mkdir(parents=True)
            (target / "provenance" / "SOURCE_MANIFEST.json").write_text(
                "{not-json\n", encoding="utf-8"
            )
            source = run_script(VERIFY_SOURCE, str(target), "--json")
            self.assertEqual(source.returncode, 2)
            self.assertEqual(json.loads(source.stdout)["status"], "error")

            report = target / "analysis" / "readiness" / "bad.json"
            report.parent.mkdir(parents=True)
            report.write_text("[not-an-object]\n", encoding="utf-8")
            readiness = run_script(
                VALIDATE_READINESS,
                str(target),
                str(report.relative_to(target)),
                "--json",
            )
            self.assertEqual(readiness.returncode, 2)
            self.assertEqual(json.loads(readiness.stdout)["status"], "error")

    def test_json_schemas_parse_and_source_entries_are_nonempty(self) -> None:
        schema_root = SKILL / "assets" / "schemas"
        schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in schema_root.glob("*.json")
        }
        self.assertEqual(
            set(schemas),
            {
                "readiness-gate-policy-v1.schema.json",
                "readiness-gate-policy-v2.schema.json",
                "research-analysis-spec-v1.schema.json",
                "research-analysis-spec-v2.schema.json",
                "research-environment-v1.schema.json",
                "research-invocation-v1.schema.json",
                "research-readiness-v1.schema.json",
                "research-readiness-v2.schema.json",
                "research-timing-check-v1.schema.json",
                "research-unit-overlap-v1.schema.json",
                "source-manifest-v1.schema.json",
            },
        )
        self.assertEqual(
            schemas["source-manifest-v1.schema.json"]["properties"]["entries"][
                "minItems"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
