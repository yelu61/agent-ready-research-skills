from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("distribution_validator", ROOT / "scripts/validate_skills.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_root = validator.ROOT
        validator.ROOT = self.root
        self.addCleanup(setattr, validator, "ROOT", self.old_root)
        self.skill = self.root / "skills/test-skill"
        (self.skill / "agents").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text('---\nname: test-skill\ndescription: Test distribution\n---\n')
        (self.skill / "agents/openai.yaml").write_text('interface:\n  default_prompt: "Use $test-skill"\n')
        (self.skill / "LICENSE").write_text((ROOT / "LICENSE").read_text())

    def test_nested_reference_cannot_depend_on_sibling_package(self):
        refs = self.skill / "references"
        refs.mkdir()
        (self.root / "skills/shared.md").write_text("outside")
        (refs / "source.md").write_text("[source](../../shared.md)")
        self.assertTrue(validator.validate_skill(self.skill))
        (refs / "source.md").write_text("[local](../SKILL.md)")
        self.assertEqual(validator.validate_skill(self.skill), [])

    def test_missing_nested_reference_is_detected(self):
        refs = self.skill / "references"
        refs.mkdir()
        (refs / "source.md").write_text("[missing](missing.md)")
        self.assertTrue(validator.validate_skill(self.skill))

    def test_evaluation_material_is_portable_and_case_ids_unique(self):
        prompt = self.skill / "test-prompts.json"
        case = {"id": "x", "prompt": "Read fixture", "material": "input.md"}
        prompt.write_text(json.dumps([case]))
        self.assertTrue(validator.validate_skill(self.skill))
        (self.skill / "input.md").write_text("Synthetic input")
        self.assertEqual(validator.validate_skill(self.skill), [])
        prompt.write_text(json.dumps([case, case]))
        self.assertTrue(validator.validate_skill(self.skill))

    def test_symlinked_resource_is_not_distributable(self):
        (self.skill / "alias").symlink_to(self.skill / "SKILL.md")
        self.assertTrue(validator.validate_skill(self.skill))


if __name__ == "__main__":
    unittest.main()
