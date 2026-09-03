#!/usr/bin/env python3
"""Verify a project source manifest against current files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from project_contracts import (
    ContractError,
    cli_error,
    load_json_object,
    resolve_project_relative,
    verify_source_manifest_document,
)


DEFAULT_MANIFEST = "provenance/SOURCE_MANIFEST.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify source files against a recorded SHA-256 baseline."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--allow-review",
        action="store_true",
        help="Return success for unverifiable entries that require human review.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    if not root.is_dir():
        return cli_error(
            f"Project directory does not exist: {root}",
            json_mode=args.json,
            project=str(root),
            manifest=args.manifest,
        )
    try:
        manifest = resolve_project_relative(root, args.manifest, must_exist=True)
        document = load_json_object(manifest)
    except ContractError as exc:
        return cli_error(
            str(exc),
            json_mode=args.json,
            project=str(root),
            manifest=args.manifest,
        )

    report = {
        "project": str(root),
        "manifest": args.manifest,
        **verify_source_manifest_document(root, document),
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(
            f"SOURCE INTEGRITY: {report['integrity_status'].upper()} | {args.manifest}"
        )
        for item in report["findings"]:
            print(
                f"[{item['level'].upper()}] {item['code']} | {item['path']} | {item['message']}"
            )
    if report["integrity_status"] == "fail":
        return 1
    if report["integrity_status"] == "review" and not args.allow_review:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
