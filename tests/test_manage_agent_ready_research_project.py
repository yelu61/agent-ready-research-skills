from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "manage-agent-ready-research-project"
SCAFFOLD = SKILL / "scripts" / "scaffold_project.py"
AUDIT = SKILL / "scripts" / "audit_project.py"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


class ManageAgentReadyResearchProjectTests(unittest.TestCase):
    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new-project"
            result = run_script(SCAFFOLD, str(target), "--profile", "research", "--json")
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
            script = target / "scripts" / "python" / "analysis.py"
            script.write_text('source = "/Users/example/private/data.csv"\n', encoding="utf-8")

            result = run_script(AUDIT, str(target), "--profile", "research", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("absolute-path", codes)


if __name__ == "__main__":
    unittest.main()

