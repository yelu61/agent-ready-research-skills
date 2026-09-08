from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "bulk-rnaseq-analysis" / "scripts" / "backend_lock.py"
SPEC = importlib.util.spec_from_file_location("bulk_backend_lock", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load backend lock helper from {SCRIPT}")
BACKEND_LOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BACKEND_LOCK)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def make_rnaseq_backend(root: Path) -> Path:
    root.mkdir()
    (root / "RNAseq_lib").mkdir()
    (root / "RNAseq_lib" / "core.R").write_text("identity\n", encoding="utf-8")
    (root / "notebooks").mkdir()
    (root / "notebooks" / "template.ipynb").write_text("{}\n", encoding="utf-8")
    (root / "references").mkdir()
    (root / "references" / "TEMPLATE_SELECTION.md").write_text(
        "templates\n", encoding="utf-8"
    )
    git(root, "init")
    git(root, "config", "user.name", "Backend Lock Test")
    git(root, "config", "user.email", "backend-lock@example.test")
    git(root, "add", "RNAseq_lib", "notebooks", "references")
    git(root, "commit", "-m", "initial")
    git(root, "remote", "add", "origin", "https://example.test/RNAseq-Templates.git")
    return root


class BackendLockTests(unittest.TestCase):
    def test_credentials_and_query_tokens_are_rejected_without_echoing_them(self):
        for value in ("https://user:SECRET@example.test/repo.git", "https://example.test/repo.git?token=SECRET", "ssh://git:SECRET@example.test/repo.git"):
            with self.subTest(scheme=value.split(":")[0]):
                with self.assertRaises(BACKEND_LOCK.BackendLockError) as caught:
                    BACKEND_LOCK.validate_source_url(value)
                self.assertNotIn("SECRET", str(caught.exception))

    def test_build_lock_records_cloneable_origin_and_full_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = make_rnaseq_backend(Path(temporary) / "backend")
            lock = BACKEND_LOCK.build_lock("rnaseq-templates", backend)
            self.assertEqual(lock["schema_version"], "research-backend-lock/v1")
            self.assertEqual(
                lock["source_url"], "https://example.test/RNAseq-Templates.git"
            )
            self.assertEqual(lock["revision"], git(backend, "rev-parse", "HEAD"))
            self.assertNotIn(str(backend), json.dumps(lock))

    def test_build_lock_rejects_local_only_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = make_rnaseq_backend(Path(temporary) / "backend")
            git(backend, "remote", "set-url", "origin", str(backend))
            with self.assertRaises(BACKEND_LOCK.BackendLockError):
                BACKEND_LOCK.build_lock("rnaseq-templates", backend)

    def test_verify_detects_revision_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = make_rnaseq_backend(Path(temporary) / "backend")
            lock = BACKEND_LOCK.build_lock("rnaseq-templates", backend)
            (backend / "RNAseq_lib" / "core.R").write_text(
                "changed\n", encoding="utf-8"
            )
            git(backend, "add", "RNAseq_lib/core.R")
            git(backend, "commit", "-m", "change")
            with self.assertRaisesRegex(
                BACKEND_LOCK.BackendLockError, "revision drift"
            ):
                BACKEND_LOCK.verify_checkout(lock, backend)

    def test_verify_detects_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = make_rnaseq_backend(Path(temporary) / "backend")
            lock = BACKEND_LOCK.build_lock("rnaseq-templates", backend)
            git(
                backend,
                "remote",
                "set-url",
                "origin",
                "https://example.test/different.git",
            )
            with self.assertRaisesRegex(
                BACKEND_LOCK.BackendLockError, "source drift"
            ):
                BACKEND_LOCK.verify_checkout(lock, backend)

    def test_materialize_uses_locked_commit_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            backend = make_rnaseq_backend(root / "backend")
            lock = BACKEND_LOCK.build_lock("rnaseq-templates", backend)
            report = BACKEND_LOCK.materialize_lock(
                lock, root / "cache", clone_source=str(backend)
            )
            materialized = Path(report["root"])
            self.assertEqual(report["status"], "materialized")
            self.assertEqual(git(materialized, "rev-parse", "HEAD"), lock["revision"])
            reused = BACKEND_LOCK.materialize_lock(
                lock, root / "cache", clone_source=str(backend)
            )
            self.assertEqual(reused["status"], "reused")

    def test_project_local_cache_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            lock_path = project / "workflows" / "bulk-rnaseq" / "backend.lock.json"
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                BACKEND_LOCK.BackendLockError, "outside the project"
            ):
                BACKEND_LOCK.ensure_external_cache(
                    lock_path, project / ".cache" / "backends"
                )

    def test_write_lock_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "backend.lock.json"
            document = {
                "schema_version": "research-backend-lock/v1",
                "backend": "rnaseq-templates",
                "source_url": "https://example.test/backend.git",
                "revision": "a" * 40,
            }
            BACKEND_LOCK.write_lock(path, document)
            with self.assertRaisesRegex(
                BACKEND_LOCK.BackendLockError, "overwrite"
            ):
                BACKEND_LOCK.write_lock(path, document)


if __name__ == "__main__":
    unittest.main()
