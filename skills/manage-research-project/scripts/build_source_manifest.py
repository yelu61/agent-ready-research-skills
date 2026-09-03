#!/usr/bin/env python3
"""Build a non-overwriting SHA-256 baseline for project source files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from project_contracts import (
    ContractError,
    SOURCE_SCHEMA,
    cli_error,
    collect_scope_files,
    portable_project_relative,
    project_relative,
    resolve_project_relative,
    sha256_regular_file,
    stable_source_id,
    utc_now,
    validate_source_manifest_document,
)
from scaffold_project import (
    DIRECTORY_OPEN_FLAGS,
    SAFE_DIRFD_SUPPORTED,
    open_directory_tree,
    write_file_exclusive,
)


DEFAULT_OUTPUT = "provenance/SOURCE_MANIFEST.json"


def build_document(
    root: Path,
    includes: list[str],
    excludes: list[str],
    source_context: dict[str, str | None],
) -> dict:
    files = collect_scope_files(root, includes, excludes)
    if not files:
        raise ContractError("No regular files were found in the requested source scope")
    entries = []
    for relative, path in files.items():
        digest, size = sha256_regular_file(path)
        entries.append(
            {
                "source_id": stable_source_id(relative, digest),
                "path": relative,
                "type": "file",
                "size_bytes": size,
                "hash_status": "recorded",
                "sha256": digest,
            }
        )
    return {
        "schema_version": SOURCE_SCHEMA,
        "generated_at": utc_now(),
        "scope_root": ".",
        "scope_include": includes,
        "scope_exclude": excludes,
        "hash_algorithm": "sha256",
        "source_context": source_context,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a source-integrity manifest without overwriting an existing baseline."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--include", action="append", dest="includes")
    parser.add_argument("--exclude", action="append", dest="excludes", default=[])
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--source-system")
    parser.add_argument("--source-reference")
    parser.add_argument(
        "--acquired-at",
        help="RFC 3339 acquisition/download time; omit when unknown rather than guessing.",
    )
    parser.add_argument("--data-freeze-id")
    parser.add_argument(
        "--access-level",
        choices=["public", "internal", "restricted", "controlled", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--subject-id-level",
        choices=["none", "deidentified", "coded", "identifiable", "unknown"],
        default="unknown",
    )
    parser.add_argument("--license-or-agreement")
    parser.add_argument(
        "--source-may-change",
        action="store_true",
        help="Record that the upstream source is mutable; the captured baseline is still verified by hash.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the manifest after reviewing the dry-run report.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    requested_root = args.project.expanduser()
    if requested_root.is_symlink():
        return cli_error(
            "Project directory must not be a symlink",
            json_mode=args.json,
            project=str(requested_root),
        )
    root = requested_root.resolve()
    if not root.is_dir():
        return cli_error(
            f"Project directory does not exist: {root}",
            json_mode=args.json,
            project=str(root),
        )
    if args.apply and not SAFE_DIRFD_SUPPORTED:
        return cli_error(
            "Safe apply requires dir_fd, O_DIRECTORY and O_NOFOLLOW; use dry-run on this platform",
            json_mode=args.json,
            project=str(root),
        )
    try:
        output = resolve_project_relative(root, args.output)
        if output.exists():
            raise ContractError(
                f"Refusing to overwrite existing manifest: {project_relative(root, output)}"
            )
        output_relative = project_relative(root, output)
        includes = [
            portable_project_relative(item) for item in (args.includes or ["data/raw"])
        ]
        excludes = [portable_project_relative(item) for item in (args.excludes or [])]
        for automatic in (".git", ".archive", output_relative):
            if automatic not in excludes:
                excludes.append(automatic)
        if len(includes) != len(set(includes)):
            raise ContractError("Duplicate --include paths are not allowed")
        if len(excludes) != len(set(excludes)):
            raise ContractError("Duplicate --exclude paths are not allowed")
        source_context = {
            "source_system": args.source_system,
            "source_reference": args.source_reference,
            "acquired_at": args.acquired_at,
            "data_freeze_id": args.data_freeze_id,
            "access_level": args.access_level,
            "subject_id_level": args.subject_id_level,
            "license_or_agreement": args.license_or_agreement,
            "immutable_expected": not args.source_may_change,
        }
        document = build_document(root, includes, excludes, source_context)
        contract_findings = validate_source_manifest_document(document)
        errors = [item for item in contract_findings if item["level"] == "error"]
        if errors:
            raise ContractError(
                "Generated manifest failed its own contract: "
                + "; ".join(
                    f"{item['path']}: {item['message']}" for item in errors
                )
            )
    except ContractError as exc:
        return cli_error(
            str(exc), json_mode=args.json, project=str(root), output=args.output
        )

    report = {
        "project": str(root),
        "output": project_relative(root, output),
        "apply": args.apply,
        "entry_count": len(document["entries"]),
        "manifest": document,
    }
    if args.apply:
        root_fd: int | None = None
        parent_fd: int | None = None
        try:
            root_fd = os.open(root, DIRECTORY_OPEN_FLAGS)
            parent_relative = Path(output_relative).parent.as_posix()
            parent_fd, _ = open_directory_tree(root_fd, parent_relative)
            content = json.dumps(
                document, ensure_ascii=False, indent=2, allow_nan=False
            ) + "\n"
            if not write_file_exclusive(parent_fd, Path(output_relative).name, content):
                raise FileExistsError("destination appeared before exclusive creation")
        except OSError as exc:
            return cli_error(
                f"Manifest was not written; nothing was overwritten: {exc}",
                json_mode=args.json,
                project=str(root),
                output=output_relative,
            )
        finally:
            if parent_fd is not None:
                os.close(parent_fd)
            if root_fd is not None:
                os.close(root_fd)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        action = "WROTE" if args.apply else "DRY RUN"
        print(f"{action}: {report['entry_count']} source file(s) -> {report['output']}")
        if not args.apply:
            print(
                "No files were changed. Re-run with --apply after reviewing this baseline."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
