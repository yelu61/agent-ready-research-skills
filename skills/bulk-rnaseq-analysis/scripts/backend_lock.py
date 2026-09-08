#!/usr/bin/env python3
"""Create, verify, and materialize immutable external backend locks."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


LOCK_SCHEMA = "research-backend-lock/v1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SCP_GIT_RE = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:.+$")
BACKEND_SENTINELS = {
    "rnaseq-templates": (
        "RNAseq_lib",
        "notebooks",
        "references/TEMPLATE_SELECTION.md",
    ),
    "tcga-toolkit": (
        "tcga_toolkit/VERSION",
        "tcga_toolkit/scripts/run_task.R",
        "tcga_toolkit/specs/README.md",
    ),
}


class BackendLockError(RuntimeError):
    pass


def run_git(root: Path | None, *args: str) -> str:
    command = ["git"]
    if root is not None:
        command.extend(["-C", str(root)])
    command.extend(args)
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BackendLockError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def validate_backend_root(root: Path, backend: str) -> Path:
    resolved = root.expanduser().resolve()
    sentinels = BACKEND_SENTINELS[backend]
    if not resolved.is_dir() or not all((resolved / item).exists() for item in sentinels):
        raise BackendLockError(
            f"{resolved} is not a valid {backend} root; missing required sentinels."
        )
    if not (resolved / ".git").exists():
        raise BackendLockError(f"{resolved} is not a Git checkout.")
    return resolved


def validate_source_url(value: str) -> str:
    if SCP_GIT_RE.fullmatch(value):
        return value
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise BackendLockError(f"Invalid backend source URL: {exc}") from exc
    if parsed.scheme not in {"https", "ssh", "git"} or not parsed.hostname:
        raise BackendLockError(
            "Backend source must be a cloneable HTTPS, SSH, git, or SCP-style Git URL."
        )
    if parsed.password or (parsed.scheme == "https" and parsed.username) or parsed.query or parsed.fragment:
        raise BackendLockError("Backend source URL must not contain credentials.")
    return value


def build_lock(backend: str, root: Path) -> dict[str, object]:
    checkout = validate_backend_root(root, backend)
    revision = run_git(checkout, "rev-parse", "HEAD").lower()
    if not COMMIT_RE.fullmatch(revision):
        raise BackendLockError("Backend HEAD is not a full Git commit hash.")
    dirty = run_git(checkout, "status", "--porcelain")
    if dirty:
        raise BackendLockError(
            "Backend checkout is dirty; commit or remove local changes before locking."
        )
    source_url = run_git(checkout, "config", "--get", "remote.origin.url")
    if not source_url:
        raise BackendLockError("Backend has no remote.origin.url.")
    return {
        "schema_version": LOCK_SCHEMA,
        "backend": backend,
        "source_url": validate_source_url(source_url),
        "revision": revision,
    }


def validate_lock(document: object) -> dict[str, str]:
    if not isinstance(document, dict):
        raise BackendLockError("Backend lock root must be a JSON object.")
    expected = {"schema_version", "backend", "source_url", "revision"}
    if set(document) != expected:
        raise BackendLockError(
            "Backend lock must contain exactly schema_version, backend, source_url, and revision."
        )
    if document.get("schema_version") != LOCK_SCHEMA:
        raise BackendLockError(f"Unsupported lock schema: {document.get('schema_version')!r}")
    backend = document.get("backend")
    if backend not in BACKEND_SENTINELS:
        raise BackendLockError(f"Unsupported backend: {backend!r}")
    source_url = document.get("source_url")
    revision = document.get("revision")
    if not isinstance(source_url, str):
        raise BackendLockError("source_url must be a string.")
    if not isinstance(revision, str) or not COMMIT_RE.fullmatch(revision):
        raise BackendLockError("revision must be a lowercase 40-character Git commit.")
    validate_source_url(source_url)
    return {
        "schema_version": LOCK_SCHEMA,
        "backend": backend,
        "source_url": source_url,
        "revision": revision,
    }


def read_lock(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise BackendLockError(f"Backend lock must be a regular file: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackendLockError(f"Cannot read backend lock: {exc}") from exc
    return validate_lock(document)


def write_lock(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise BackendLockError(f"Refusing to overwrite existing lock: {path}") from exc


def verify_checkout(
    lock: dict[str, str], root: Path, *, verify_source: bool = True
) -> dict[str, str]:
    checkout = validate_backend_root(root, lock["backend"])
    revision = run_git(checkout, "rev-parse", "HEAD").lower()
    if revision != lock["revision"]:
        raise BackendLockError(
            f"Backend revision drift: expected {lock['revision']}, found {revision}."
        )
    dirty = run_git(checkout, "status", "--porcelain")
    if dirty:
        raise BackendLockError("Backend checkout has uncommitted or untracked changes.")
    source_url = run_git(checkout, "config", "--get", "remote.origin.url")
    if verify_source:
        validate_source_url(source_url)
    if verify_source and source_url != lock["source_url"]:
        raise BackendLockError("Backend source drift: origin differs from the locked source.")
    return {
        "status": "verified",
        "backend": lock["backend"],
        "revision": revision,
        "root": str(checkout),
    }


def default_cache_root() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    if configured:
        base = Path(configured).expanduser()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path.home() / ".cache"
    return base / "agent-ready-research" / "backends"


def project_root_from_lock(lock_path: Path) -> Path | None:
    resolved = lock_path.expanduser().resolve()
    if (
        resolved.name == "backend.lock.json"
        and resolved.parent.parent.name == "workflows"
    ):
        return resolved.parent.parent.parent
    return None


def ensure_external_cache(lock_path: Path, cache_root: Path) -> Path:
    resolved = cache_root.expanduser().resolve()
    project_root = project_root_from_lock(lock_path)
    if project_root is not None:
        try:
            resolved.relative_to(project_root)
        except ValueError:
            pass
        else:
            raise BackendLockError(
                "Backend cache must be outside the project containing the lock."
            )
    return resolved


def materialize_lock(
    lock: dict[str, str],
    cache_root: Path,
    *,
    clone_source: str | None = None,
) -> dict[str, str]:
    destination = cache_root / lock["backend"] / lock["revision"]
    if destination.exists():
        report = verify_checkout(
            lock, destination, verify_source=clone_source is None
        )
        report["status"] = "reused"
        return report

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{lock['backend']}-", dir=destination.parent)
    )
    try:
        run_git(
            None,
            "clone",
            "--no-checkout",
            clone_source or lock["source_url"],
            str(temporary),
        )
        run_git(temporary, "checkout", "--detach", lock["revision"])
        verify_checkout(lock, temporary, verify_source=clone_source is None)
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {
        "status": "materialized",
        "backend": lock["backend"],
        "revision": lock["revision"],
        "root": str(destination),
    }


def emit(payload: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a non-overwriting backend lock")
    create.add_argument("--backend", choices=sorted(BACKEND_SENTINELS), required=True)
    create.add_argument("--root", type=Path, required=True)
    create.add_argument(
        "--output",
        type=Path,
        default=Path("workflows/bulk-rnaseq/backend.lock.json"),
    )
    create.add_argument("--json", action="store_true")

    verify = commands.add_parser("verify", help="Verify a checkout against a lock")
    verify.add_argument("--lock", type=Path, required=True)
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--json", action="store_true")

    materialize = commands.add_parser(
        "materialize", help="Clone and detach the locked backend in an external cache"
    )
    materialize.add_argument("--lock", type=Path, required=True)
    materialize.add_argument("--cache-root", type=Path)
    materialize.add_argument("--json", action="store_true")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "create":
            lock = build_lock(args.backend, args.root)
            write_lock(args.output, lock)
            emit({"status": "created", "path": str(args.output), **lock}, args.json)
            return 0
        lock = read_lock(args.lock)
        if args.command == "verify":
            emit(verify_checkout(lock, args.root), args.json)
            return 0
        cache_root = ensure_external_cache(
            args.lock, args.cache_root or default_cache_root()
        )
        emit(materialize_lock(lock, cache_root), args.json)
        return 0
    except (BackendLockError, OSError) as exc:
        if getattr(args, "json", False):
            emit({"status": "error", "error": str(exc)}, True)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 4 if args.command == "verify" else 1


if __name__ == "__main__":
    raise SystemExit(main())
