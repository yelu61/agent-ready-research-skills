from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "manage-research-project"
TEMPLATES = SKILL / "assets" / "exploratory"
MODULE_PATH = SKILL / "scripts" / "exploratory_profile.py"
SCAFFOLD = SKILL / "scripts" / "scaffold_project.py"
AUDIT = SKILL / "scripts" / "audit_project.py"
SPEC = importlib.util.spec_from_file_location("exploratory_profile_tested", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_cli(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        check=False, capture_output=True, text=True,
    )


def project_map() -> dict[str, object]:
    return {
        "schema_version": "research-project-map/v1",
        "docs_root": "project_records",
        "source_roots": ["code"],
        "raw_roots": ["source_data"],
        "run_root": "execution_records",
        "results_root": "deliverables",
    }


def write_memory(root: Path, updated: str | None = None) -> None:
    for name in MODULE.EXPLORATORY_FILES:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        for key, value in {
            "PROJECT_NAME": "A pilot",
            "OBJECTIVE": "Inspect cell-type evidence for the proposed comparison.",
            "DATE": updated or date.today().isoformat(),
        }.items():
            text = text.replace("{{" + key + "}}", value)
        (root / name).write_text(text, encoding="utf-8")


class ExploratoryProfileTests(unittest.TestCase):
    def test_cli_dry_run_proposes_four_files_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "pilot"
            result = run_cli(SCAFFOLD, str(target), "--profile", "exploratory", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["apply"])
            self.assertEqual(report["create_directories"], [])
            self.assertEqual(set(report["create_files"]), set(MODULE.EXPLORATORY_FILES))
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_cli_apply_creates_only_four_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "pilot"
            result = run_cli(
                SCAFFOLD, str(target), "--profile", "exploratory", "--apply", "--json",
                "--objective", "Assess whether sample metadata support the planned comparison.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(path.name for path in target.iterdir()), set(MODULE.EXPLORATORY_FILES))
            self.assertTrue(all(path.is_file() for path in target.iterdir()))
            self.assertTrue(MODULE.is_exploratory(target))
            self.assertEqual(MODULE.audit_exploratory(target, 30), [])

    def test_cli_repeated_apply_preserves_written_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "pilot"
            first = run_cli(SCAFFOLD, str(target), "--profile", "exploratory", "--apply", "--json")
            self.assertEqual(first.returncode, 0, first.stderr)
            notes = target / "PROJECT_NOTES.md"
            with notes.open("a", encoding="utf-8") as handle:
                handle.write("\nPilot observation: the metadata have not yet been supplied.\n")
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            again = run_cli(SCAFFOLD, str(target), "--profile", "exploratory", "--apply", "--json")
            self.assertEqual(again.returncode, 0, again.stderr)
            report = json.loads(again.stdout)
            self.assertEqual(report["create_files"], [])
            self.assertEqual(report["create_directories"], [])
            self.assertEqual(set(report["skip_existing_files"]), set(MODULE.EXPLORATORY_FILES))
            self.assertEqual(before, {path.name: path.read_bytes() for path in target.iterdir()})

    def test_cli_audit_auto_selects_exploratory_without_assessing_science(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_memory(root)
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            result = run_cli(AUDIT, str(root), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["profile"], "exploratory")
            self.assertEqual(report["audit_kind"], "exploratory-memory")
            self.assertEqual(report["scientific_readiness"], "not_assessed")
            self.assertEqual(report["source_integrity"], "not_assessed")
            self.assertEqual(report["findings"], [])
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})

    def test_cli_formal_records_take_precedence_over_retained_exploratory_marker(self) -> None:
        formal_records = {
            "PROJECT_MAP.json": json.dumps(project_map()),
            "docs/ANALYSIS_PLAN.md": "# Formal analysis plan\nReview the sample-level contrast.\n",
            "provenance/RUNS.tsv": "run_id\tstatus\n",
            "provenance/PROJECT_LAYOUT.json": (
                SKILL / "assets" / "templates" / "provenance" / "PROJECT_LAYOUT.json"
            ).read_text(encoding="utf-8"),
        }
        for relative, content in formal_records.items():
            with self.subTest(record=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_memory(root)
                formal = root / relative
                formal.parent.mkdir(parents=True, exist_ok=True)
                formal.write_text(content, encoding="utf-8")
                # The old notes remain recognizable; only the outer profile router changes.
                self.assertTrue(MODULE.is_exploratory(root))
                result = run_cli(AUDIT, str(root), "--json")
                self.assertTrue(result.stdout, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["profile"], "research")
                self.assertEqual(report["audit_kind"], "structure")
                self.assertEqual(report["scientific_readiness"], "not_assessed")
                self.assertEqual(formal.read_text(encoding="utf-8"), content)

    def test_cli_exploratory_with_formal_layout_map_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            supplied = base / "map.json"
            supplied.write_text(json.dumps(project_map()), encoding="utf-8")
            target = base / "pilot"
            scaffold = run_cli(
                SCAFFOLD, str(target), "--profile", "exploratory", "--layout-map", str(supplied), "--apply", "--json",
            )
            self.assertNotEqual(scaffold.returncode, 0)
            conflicts = json.loads(scaffold.stdout)["conflicts"]
            self.assertIn("Exploratory", conflicts[0]["reason"])
            self.assertFalse(target.exists())
            target.mkdir()
            write_memory(target)
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            audit = run_cli(AUDIT, str(target), "--profile", "exploratory", "--layout-map", str(supplied), "--json")
            self.assertNotEqual(audit.returncode, 0)
            findings = json.loads(audit.stdout)["findings"]
            self.assertIn("exploratory-layout-map", {item["code"] for item in findings})
            self.assertEqual(before, {path.name: path.read_bytes() for path in target.iterdir()})

    def test_four_files_without_directories_are_sufficient(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_memory(root)
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            self.assertEqual(set(before), set(MODULE.EXPLORATORY_FILES))
            self.assertTrue(MODULE.is_exploratory(root))
            self.assertEqual(MODULE.audit_exploratory(root, 30), [])
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})

    def test_missing_or_incidental_marker_does_not_select_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertFalse(MODULE.is_exploratory(root))
            write_memory(root)
            notes = root / "PROJECT_NOTES.md"
            notes.write_text(notes.read_text().replace(MODULE.PROFILE_MARKER, "quoted: " + MODULE.PROFILE_MARKER))
            self.assertFalse(MODULE.is_exploratory(root))
            self.assertIn("exploratory-marker", {item["code"] for item in MODULE.audit_exploratory(root, 30)})

    def test_incomplete_notes_and_absent_file_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_memory(root)
            (root / "CLAUDE.md").unlink()
            notes = root / "PROJECT_NOTES.md"
            notes.write_text(MODULE.PROFILE_MARKER + "\n## Question\n\nA pilot\n")
            findings = MODULE.audit_exploratory(root, 30)
            codes = {item["code"] for item in findings}
            self.assertTrue({"missing-file", "missing-date", "exploratory-note-section"} <= codes)
            self.assertTrue(all(set(item) == {"level", "code", "path", "message"} for item in findings))

    def test_freshness_and_invalid_dates_are_not_silent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value, expected in (
                ((date.today() - timedelta(days=31)).isoformat(), "stale-document"),
                ((date.today() + timedelta(days=1)).isoformat(), "future-date"),
                ("2026-02-30", "invalid-date"),
                ("20260908", "invalid-date"),
            ):
                with self.subTest(value=value):
                    write_memory(root, value)
                    self.assertIn(expected, {item["code"] for item in MODULE.audit_exploratory(root, 30)})
            for stale in (-1, True, "30"):
                with self.assertRaises(ValueError):
                    MODULE.audit_exploratory(root, stale)

    def test_symlinked_memory_and_root_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            write_memory(root)
            outside = base / "outside.md"
            outside.write_text(MODULE.PROFILE_MARKER)
            notes = root / "PROJECT_NOTES.md"
            notes.unlink()
            notes.symlink_to(outside)
            self.assertFalse(MODULE.is_exploratory(root))
            self.assertIn("path-symlink", {item["code"] for item in MODULE.audit_exploratory(root, 30)})
            alias = base / "alias"
            alias.symlink_to(root, target_is_directory=True)
            self.assertFalse(MODULE.is_exploratory(alias))
            self.assertIn("path-symlink", {item["code"] for item in MODULE.audit_exploratory(alias, 30)})
            self.assertEqual(outside.read_text(), MODULE.PROFILE_MARKER)

    def test_hardlink_and_nonregular_memory_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            write_memory(root)
            os.link(root / "PROJECT_NOTES.md", base / "notes-alias.md")
            self.assertFalse(MODULE.is_exploratory(root))
            self.assertIn("path-hardlink", {item["code"] for item in MODULE.audit_exploratory(root, 30)})
            agents = root / "AGENTS.md"
            agents.unlink()
            agents.mkdir()
            self.assertIn("file-type", {item["code"] for item in MODULE.audit_exploratory(root, 30)})

    def test_large_or_non_utf8_memory_reports_error_without_modification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_memory(root)
            notes = root / "PROJECT_NOTES.md"
            for content, expected in ((b"x" * (MODULE.MAX_MEMORY_BYTES + 1), "memory-file-too-large"), (b"\xff", "memory-read")):
                with self.subTest(expected=expected):
                    notes.write_bytes(content)
                    self.assertFalse(MODULE.is_exploratory(root))
                    self.assertIn(expected, {item["code"] for item in MODULE.audit_exploratory(root, 30)})
                    self.assertEqual(notes.read_bytes(), content)

    def test_linked_data_are_not_read_or_required_by_structure_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_memory(root)
            notes = root / "PROJECT_NOTES.md"
            with notes.open("a") as handle:
                handle.write("\nExisting record: [analysis log](records/log.md).\n")
            self.assertEqual(MODULE.audit_exploratory(root, 30), [])
            self.assertFalse((root / "records").exists())


if __name__ == "__main__":
    unittest.main()
