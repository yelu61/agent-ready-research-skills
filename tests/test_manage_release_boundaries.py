from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/manage-research-project/scripts"


class ReleaseBoundaryTests(unittest.TestCase):
    def test_all_manager_references_have_a_discovery_path(self):
        skill = SCRIPTS.parent.resolve()
        pending = [skill / "SKILL.md"]
        visited = set()
        while pending:
            document = pending.pop()
            if document in visited:
                continue
            visited.add(document)
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
                target = target.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resource = (document.parent / target).resolve()
                if resource.is_relative_to(skill) and resource.is_file() and resource.suffix == ".md":
                    pending.append(resource)
        references = set((skill / "references").rglob("*.md"))
        self.assertTrue(references)
        self.assertEqual(references - visited, set(), "A bundled reference lost its on-demand entry path")

    def test_v2_cli_cannot_silently_authorize_a_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "v2.json"
            payload = '{"schema_version":"research-readiness/v2","readiness_status":"ready"}'
            report.write_text(payload)
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_scientific_readiness.py"),
                 str(root), "v2.json", "--require-ready", "--json"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(json.loads(result.stdout)["use_permitted"])
            self.assertEqual(report.read_text(), payload)
            self.assertEqual([p.name for p in root.iterdir()], ["v2.json"])

    def test_registry_missing_locking_support_is_a_contract_error(self):
        old_path = sys.path[:]
        try:
            sys.path.insert(0, str(SCRIPTS))
            spec = importlib.util.spec_from_file_location("register_release_test", SCRIPTS / "register_run.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with patch.object(module.importlib, "import_module", side_effect=ImportError("unavailable")):
                with self.assertRaises(module.ContractError):
                    module.append_runtime()
        finally:
            sys.path[:] = old_path


if __name__ == "__main__":
    unittest.main()
