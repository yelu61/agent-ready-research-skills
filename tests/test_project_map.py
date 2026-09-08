from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'skills/manage-research-project'


class ProjectMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'project'
        self.root.mkdir()
        self.mapping = json.loads((SKILL / 'assets/examples/project-map.json').read_text())
        self.config = self.base / 'mapping.json'
        self.save()

    def save(self):
        self.config.write_text(json.dumps(self.mapping))

    def run_cli(self, name, *args):
        result = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts' / name), str(self.root), *args, '--json'], capture_output=True, text=True)
        self.assertNotIn('Traceback', result.stderr)
        return result, json.loads(result.stdout)

    def scaffold(self, *args):
        return self.run_cli('scaffold_project.py', '--layout-map', str(self.config), *args)

    def snapshot(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_retrofit_preserves_existing_paths_and_content_then_audits_mapping(self):
        for folder in ('src', 'notebooks', 'inputs/raw', 'notes', 'outputs/runs', 'reports'):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        for relative, contents in {'src/analysis.R': 'x <- 1\n', 'inputs/raw/counts.tsv': 'gene\tS1\nG1\t1\n',
                                   'notes/current.md': '# Status\nLast updated: 2026-09-08\n## Next minimal executable task\nReview counts\n'}.items():
            (self.root / relative).write_text(contents)
        before = self.snapshot()
        result, report = self.scaffold('--apply')
        self.assertEqual(result.returncode, 0, report)
        for path, digest in before.items():
            self.assertEqual(self.snapshot()[path], digest)
        for relative in ('workflows', 'docs', 'data', 'provenance/PROJECT_LAYOUT.json'):
            self.assertFalse((self.root / relative).exists(), relative)
        self.assertEqual(json.loads((self.root / 'PROJECT_MAP.json').read_text()), self.mapping)
        for relative in ('notes/PIPELINE.md', 'notes/REPRODUCIBILITY.md', 'notes/DATA_DICTIONARY.md'):
            contents = (self.root / relative).read_text()
            self.assertNotIn('workflows/', contents)
            self.assertNotIn('data/raw/', contents)
            self.assertNotIn('{{', contents)
        pipeline = (self.root / 'notes/PIPELINE.md').read_text()
        self.assertIn('outputs/runs', pipeline)
        self.assertIn('reports', pipeline)
        result, report = self.run_cli('audit_project.py')
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(report['layout_generation'], 'mapped')
        self.assertEqual(report['scientific_readiness'], 'not_assessed')
        self.assertFalse(any(f['code'] == 'missing-file' for f in report['findings']))
        self.assertTrue(all(f['path'] == 'notes/' for f in report['findings'] if f['code'] == 'todo-count'))
        (self.root / 'notes/next-session.md').write_text('# Handoff\nLast updated: 2026-09-08\n\n## Next minimal executable task\nDifferent task\n')
        _, mismatch = self.run_cli('audit_project.py')
        self.assertTrue(any(f['code'] == 'next-task-mismatch' and f['path'] == 'notes/next-session.md' for f in mismatch['findings']))
        (self.root / 'notes/current.md').unlink()
        _, report = self.run_cli('audit_project.py')
        self.assertTrue(any(f['code'] == 'missing-file' and f['path'] == 'notes/current.md' for f in report['findings']))

    def test_dry_run_and_explicit_audit_never_persist_mapping(self):
        before = self.snapshot()
        result, report = self.scaffold()
        self.assertEqual(result.returncode, 0, report)
        self.assertIn('PROJECT_MAP.json', report['create_files'])
        self.run_cli('audit_project.py', '--layout-map', str(self.config))
        self.assertEqual(self.snapshot(), before)

    def test_external_map_selects_formal_audit_over_retained_exploratory_marker(self):
        self.run_cli('scaffold_project.py', '--profile', 'exploratory', '--apply')
        before = self.snapshot()
        _, report = self.run_cli('audit_project.py', '--layout-map', str(self.config))
        self.assertEqual(report['profile'], 'research')
        self.assertEqual(report['layout_generation'], 'mapped')
        self.assertEqual(self.snapshot(), before)

    def test_mapped_raw_protection_check_uses_actual_roots(self):
        self.scaffold('--apply')
        agents = self.root / 'AGENTS.md'
        agents.write_text('Never modify data/raw.\n')
        _, report = self.run_cli('audit_project.py')
        self.assertTrue(any(f['code'] == 'raw-protection' for f in report['findings']))
        agents.write_text('Never modify inputs/raw.\n')
        _, report = self.run_cli('audit_project.py')
        self.assertFalse(any(f['code'] == 'raw-protection' for f in report['findings']))

    def test_mapped_init_has_no_default_source_or_data_roots(self):
        result, report = self.scaffold('--mode', 'init', '--apply')
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue((self.root / 'src').is_dir())
        self.assertTrue((self.root / 'inputs/raw').is_dir())
        self.assertTrue((self.root / 'reports/README.md').is_file())
        self.assertFalse((self.root / 'workflows').exists())
        self.assertFalse((self.root / 'analysis/runs').exists())
        self.assertFalse((self.root / 'data').exists())

    def test_modified_saved_mapping_is_not_overwritten(self):
        self.assertEqual(self.scaffold('--apply')[0].returncode, 0)
        before = self.snapshot()
        self.mapping['docs_root'] = 'different-notes'
        self.save()
        result, _ = self.scaffold('--apply')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_nested_default_named_roots_are_rendered_once(self):
        self.mapping['run_root'] = 'analysis/runs/cache'
        self.mapping['results_root'] = 'results/reviewed'
        self.save()
        result, report = self.scaffold('--apply')
        self.assertEqual(result.returncode, 0, report)
        content = (self.root / 'README.md').read_text()
        self.assertIn('Native runs: analysis/runs/cache\n', content)
        self.assertIn('Reviewed results: results/reviewed\n', content)

    def test_explicit_map_never_uses_implicit_legacy_pipeline(self):
        (self.root / 'PIPELINE.md').write_text('Historical flow\n')
        self.mapping['docs_root'] = 'docs'
        self.save()
        result, report = self.scaffold('--apply')
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue((self.root / 'docs/PIPELINE.md').is_file())
        self.assertEqual(report['accepted_equivalent_files'], [])
        (self.root / 'docs/PIPELINE.md').unlink()
        _, audit = self.run_cli('audit_project.py')
        self.assertTrue(any(f['code'] == 'missing-file' and f['path'] == 'docs/PIPELINE.md' for f in audit['findings']))
        self.assertEqual((self.root / 'PIPELINE.md').read_text(), 'Historical flow\n')

    def test_case_aliases_and_manuscript_collisions_are_rejected(self):
        for value in ('notes/NEXT-SESSION.md', 'MANUSCRIPT/author_queries.md', 'notes', 'notes/next-session.md/child.md'):
            with self.subTest(value=value):
                self.mapping['documents']['docs/PROJECT_STATUS.md'] = value
                self.save()
                result, _ = self.scaffold('--profile', 'manuscript', '--apply')
                self.assertEqual(result.returncode, 1)
                self.assertEqual(list(self.root.iterdir()), [])
        self.mapping['documents'].pop('docs/PROJECT_STATUS.md')
        self.mapping['results_root'] = 'INPUTS/RAW/reports'
        self.save()
        self.assertEqual(self.scaffold('--apply')[0].returncode, 1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_map_rejects_overlapping_roles_before_writing(self):
        for key, value in [('results_root', 'inputs/raw/report'), ('run_root', 'src/runs'), ('docs_root', 'provenance/notes')]:
            with self.subTest(key=key):
                original = self.mapping[key]
                self.mapping[key] = value
                self.save()
                result, report = self.scaffold('--apply')
                self.assertEqual(result.returncode, 1, report)
                self.assertEqual(list(self.root.iterdir()), [])
                self.mapping[key] = original

    def test_document_override_cannot_write_raw_data_or_shadow_another_role(self):
        for value in ('inputs/raw/counts.tsv', 'notes/ANALYSIS_PLAN.md', 'provenance/RUNS.tsv', '../outside.md'):
            with self.subTest(value=value):
                self.mapping['documents']['docs/PROJECT_STATUS.md'] = value
                self.save()
                result, _ = self.scaffold('--apply')
                self.assertEqual(result.returncode, 1)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_roots_and_symlink_ancestors_are_rejected(self):
        for value in ('../outside', '/absolute', 'notes//nested', '.git/notes', '.'):
            with self.subTest(value=value):
                self.mapping['docs_root'] = value
                self.save()
                self.assertEqual(self.scaffold('--apply')[0].returncode, 1)
        self.mapping['docs_root'] = 'notes'
        self.save()
        (self.root / 'notes').symlink_to(self.base, target_is_directory=True)
        result, _ = self.scaffold('--apply')
        self.assertEqual(result.returncode, 1)
        self.assertEqual([p.name for p in self.root.iterdir()], ['notes'])

    def test_fixed_v2_and_map_cannot_silently_compete(self):
        self.run_cli('scaffold_project.py', '--apply')
        before = self.snapshot()
        result, _ = self.scaffold('--apply')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.snapshot(), before)

    def test_audit_scans_mapped_source_not_raw_and_keeps_source_integrity(self):
        self.scaffold('--apply')
        (self.root / 'src').mkdir(exist_ok=True)
        (self.root / 'inputs/raw').mkdir(parents=True, exist_ok=True)
        (self.root / 'src/run.py').write_text("path = '/Users/example/data'\n")
        (self.root / 'inputs/raw/acquisition.md').write_text('/Users/instrument/original')
        _, report = self.run_cli('audit_project.py')
        found = [f['path'] for f in report['findings'] if f['code'] == 'absolute-path']
        self.assertEqual(found, ['src/run.py'])
        result = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts/build_source_manifest.py'), str(self.root), '--apply', '--json'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['manifest']['scope_include'], ['inputs/raw'])
        (self.root / 'inputs/raw/acquisition.md').write_text('changed bytes')
        _, report = self.run_cli('audit_project.py')
        self.assertEqual(report['source_integrity'], 'fail')

    def test_malformed_saved_map_is_an_error_not_a_legacy_success(self):
        (self.root / 'PROJECT_MAP.json').write_text('{"schema_version":"bad"}')
        result, report = self.run_cli('audit_project.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(f['code'] == 'project-map-invalid' for f in report['findings']))


if __name__ == '__main__':
    unittest.main()
