from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "manage-research-project"
SCAFFOLD = SKILL / "scripts" / "scaffold_project.py"
AUDIT = SKILL / "scripts" / "audit_project.py"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


class ManageResearchProjectTests(unittest.TestCase):
    def test_new_research_scaffold_uses_layout_v2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new-project"
            result = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "research",
                "--apply",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            layout = json.loads(
                (target / "provenance" / "PROJECT_LAYOUT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(layout["schema_version"], "research-project-layout/v2")
            self.assertTrue((target / "workflows").is_dir())
            self.assertTrue((target / "data" / "references").is_dir())
            self.assertTrue((target / "docs" / "PIPELINE.md").is_file())
            self.assertTrue((target / "results" / "README.md").is_file())
            for relative in (
                "scripts",
                "notebooks",
                "analysis/config",
                "analysis/scripts",
                "analysis/notebooks",
                "results/tables",
                "results/figures",
                "results/reports",
                "results/intermediate",
                "PIPELINE.md",
            ):
                self.assertFalse((target / relative).exists(), relative)

    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new-project"
            result = run_script(
                SCAFFOLD, str(target), "--profile", "research", "--json"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["apply"])
            self.assertFalse(target.exists())

    def test_manuscript_scaffold_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "manuscript-project"
            first = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "manuscript",
                "--apply",
                "--json",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((target / "manuscript" / "FIGURE_MANIFEST.tsv").is_file())

            second = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "manuscript",
                "--apply",
                "--json",
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads(second.stdout)
            self.assertEqual(report["create_files"], [])
            self.assertGreater(len(report["skip_existing_files"]), 0)

    def test_retrofit_preserves_existing_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "existing-project"
            target.mkdir()
            readme = target / "README.md"
            readme.write_text("preserve me\n", encoding="utf-8")
            result = run_script(
                SCAFFOLD,
                str(target),
                "--mode",
                "retrofit",
                "--profile",
                "research",
                "--apply",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(readme.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse((target / "workflows").exists())
            self.assertFalse(
                (target / "provenance" / "PROJECT_LAYOUT.json").exists()
            )
            self.assertFalse((target / "results" / "README.md").exists())
            self.assertTrue((target / "PIPELINE.md").is_file())

    def test_retrofit_accepts_existing_pipeline_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "existing-project"
            target.mkdir()
            (target / "README.md").write_text("legacy\n", encoding="utf-8")
            (target / "docs").mkdir()
            (target / "docs" / "PIPELINE.md").write_text(
                "accepted equivalent\n", encoding="utf-8"
            )
            result = run_script(
                SCAFFOLD,
                str(target),
                "--mode",
                "retrofit",
                "--profile",
                "research",
                "--apply",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse((target / "PIPELINE.md").exists())
            self.assertIn(
                {"canonical": "PIPELINE.md", "existing": "docs/PIPELINE.md"},
                report["accepted_equivalent_files"],
            )

    def test_retrofit_rejects_symlinked_project_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / "docs").symlink_to(outside, target_is_directory=True)

            result = run_script(
                SCAFFOLD,
                str(target),
                "--mode",
                "retrofit",
                "--profile",
                "minimal",
                "--apply",
                "--json",
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertTrue(report["conflicts"])
            self.assertEqual(list(outside.iterdir()), [])

    def test_audit_reports_machine_specific_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "research",
                "--apply",
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            script = target / "workflows" / "test" / "scripts" / "analysis.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                'source = "/Users/example/private/data.csv"\n', encoding="utf-8"
            )

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("absolute-path", codes)

    def test_audit_reports_windows_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "research",
                "--apply",
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            script = target / "workflows" / "test" / "scripts" / "analysis.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                "source = r'C:\\Users\\example\\data.csv'\n",
                encoding="utf-8",
            )

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("absolute-path", codes)

    def test_audit_reports_windows_unc_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD,
                str(target),
                "--profile",
                "research",
                "--apply",
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            script = target / "workflows" / "test" / "scripts" / "analysis.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                r"source = r'\\server\share\data.csv'" + "\n",
                encoding="utf-8",
            )

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("absolute-path", codes)

    def test_v2_audit_rejects_parallel_roots_and_embedded_backend(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD, str(target), "--profile", "research", "--apply"
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            (target / "scripts").mkdir()
            (target / "scripts" / "run.R").write_text("1\n", encoding="utf-8")
            (target / "analysis" / "backend").mkdir(parents=True)
            (target / "results" / "tables").mkdir()
            (target / "PIPELINE.md").write_text("legacy\n", encoding="utf-8")

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertEqual(report["layout_generation"], "v2")
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("parallel-analysis-source-root", codes)
            self.assertIn("embedded-backend", codes)
            self.assertNotIn("type-first-results", codes)
            self.assertIn("legacy-pipeline-location", codes)

    def test_v2_composes_workflow_run_and_question_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD, str(target), "--profile", "research", "--apply"
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            workflow = target / "workflows" / "bulk-rnaseq"
            for child in ("config", "scripts", "notebooks"):
                (workflow / child).mkdir(parents=True, exist_ok=True)
            (workflow / "README.md").write_text("Bulk RNA-seq\n", encoding="utf-8")
            (workflow / "config" / "main.R").write_text("seed <- 1\n", encoding="utf-8")
            (workflow / "scripts" / "run.R").write_text("print('run')\n", encoding="utf-8")
            (workflow / "backend.lock.json").write_text(
                json.dumps(
                    {
                        "schema_version": "research-backend-lock/v1",
                        "backend": "rnaseq-templates",
                        "source_url": "https://example.test/RNAseq-Templates.git",
                        "revision": "a" * 40,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (target / "analysis" / "runs" / "bulk-rnaseq__main-01").mkdir(
                parents=True
            )
            question = target / "results" / "treatment-vs-control"
            for child in ("tables", "figures", "report"):
                (question / child).mkdir(parents=True)
            # Modules and top-level report navigation are also valid choices.
            (target / "results" / "03_ORA" / "tables").mkdir(parents=True)
            (target / "results" / "reports").mkdir()

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["layout_generation"], "v2")
            self.assertFalse(
                any(finding["level"] == "error" for finding in report["findings"])
            )

    def test_v2_audit_rejects_changed_layout_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            scaffold = run_script(
                SCAFFOLD, str(target), "--profile", "research", "--apply"
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            layout_path = target / "provenance" / "PROJECT_LAYOUT.json"
            layout = json.loads(layout_path.read_text(encoding="utf-8"))
            layout["workflow_source_root"] = "analysis/scripts"
            layout_path.write_text(json.dumps(layout) + "\n", encoding="utf-8")

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 1)
            codes = {
                finding["code"]
                for finding in json.loads(result.stdout)["findings"]
            }
            self.assertIn("layout-path", codes)

    def test_legacy_audit_accepts_root_pipeline_without_requiring_v2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "legacy"
            target.mkdir()
            scaffold = run_script(
                SCAFFOLD,
                str(target),
                "--mode",
                "retrofit",
                "--profile",
                "research",
                "--apply",
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["layout_generation"], "legacy")
            self.assertFalse(
                any(
                    finding["path"] == "docs/PIPELINE.md"
                    and finding["code"] == "missing-file"
                    for finding in report["findings"]
                )
            )


if __name__ == "__main__":
    unittest.main()
