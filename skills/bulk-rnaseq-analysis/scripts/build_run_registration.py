#!/usr/bin/env python3
"""Map an RNAseq-Templates native run to the generic project run registry input."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


REFERENCE_ROLES = {"annotation_db", "go_reference", "kegg_reference", "ortholog_cache", "iobr_references"}


def local_file(root: Path, path: Path) -> Path:
    # Native inputs can be relative to the run (including ../), but the final
    # normalized file must be inside the project and have no symlink component.
    absolute = Path(os.path.abspath(path))
    relative = absolute.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink component: " + relative.as_posix())
    if not absolute.is_file():
        raise ValueError("Missing regular file: " + relative.as_posix())
    return absolute


def read_rows(path: Path, delimiter: str = ",") -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def checksum(path: Path, algorithm: str = "md5") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def native_file(root: Path, run_dir: Path, raw: str, *, digest: str | None = None,
                path_base: str = "", allow_external: bool = False, label: str = "Native file") -> Path:
    if not raw or path_base not in {"", "run"}:
        raise ValueError("Native path is missing or path_base is unsupported")
    if path_base == "run" and Path(raw).is_absolute():
        raise ValueError("path_base=run requires a run-relative path: " + label)
    bases = [run_dir] if path_base == "run" else [run_dir, root]
    candidates = list(dict.fromkeys(Path(os.path.abspath(base / raw)) for base in bases))
    matches, found, external_disallowed = [], False, False
    for candidate in candidates:
        if not candidate.is_file():
            continue
        found = True
        if candidate.is_relative_to(root):
            path = local_file(root, candidate)
        elif allow_external:
            path = candidate.resolve(strict=True)
        else:
            external_disallowed = True
            continue
        if digest is None or checksum(path) == digest:
            if path not in matches:
                matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError("Ambiguous legacy native path; run/project candidates both match: " + label)
    if external_disallowed:
        raise ValueError("External non-reference input must be registered in the project: " + label)
    if found:
        raise ValueError(label + " checksum mismatch")
    if path_base == "run":
        raise ValueError("Native run-relative path cannot be resolved: " + label)
    raise ValueError("Native path cannot be resolved: " + label +
                     "; legacy basename-only references may have lost their location. "
                     "Restore explicit provenance; do not guess a file by basename.")


def build(root: Path, run_dir: Path, entry_point: str, delivery: Path | None = None,
          parent_run_dir: Path | None = None) -> dict:
    native = read_rows(local_file(root, run_dir / "run_manifest.csv"))
    if len(native) != 1 or native[0].get("manifest_schema_version") != "2":
        raise ValueError("Expected one schema-v2 native run manifest row")
    native = native[0]
    if native.get("run_id") != run_dir.name:
        raise ValueError("Native run_id does not match the run directory")
    source_roots = {native["run_id"]: run_dir}
    if parent_run_dir:
        parent = read_rows(local_file(root, parent_run_dir / "run_manifest.csv"))
        if (len(parent) != 1 or parent[0].get("manifest_schema_version") != "2"
                or parent[0].get("run_id") != parent_run_dir.name
                or native.get("parent_run_id") != parent[0]["run_id"]):
            raise ValueError("Parent native manifest does not match derivative parent_run_id")
        source_roots[parent[0]["run_id"]] = parent_run_dir
    path_base = native.get("path_base", "")
    inputs_file = native_file(root, run_dir, native["input_manifest_file"],
                              digest=native["input_manifest_md5"], path_base=path_base,
                              label="Native input manifest")
    config = native_file(root, run_dir, native["config_file"], digest=native["config_md5"],
                        path_base=path_base, label="Native config")
    if entry_point.startswith("backend:rnaseq-templates/"):
        # Preserve the caller's actual locked-backend entry identity without
        # forcing a project wrapper. This does not satisfy a scientific code
        # coverage assessment; that remains a separate domain contract.
        entry = entry_point.removeprefix("backend:rnaseq-templates/")
        if Path(entry).is_absolute() or ".." in Path(entry).parts or "\\" in entry:
            raise ValueError("Invalid backend-relative entry point")
    else:
        entry_point = local_file(root, root / entry_point).relative_to(root).as_posix()
    runtime = native_file(root, run_dir, native["runtime_manifest_file"], path_base=path_base,
                         label="Native runtime manifest")
    relative = lambda path: path.relative_to(root).as_posix()
    rows, seen, reference_paths, warnings = [], set(), set(), []
    for row_number, item in enumerate(read_rows(inputs_file), start=2):
        if item["status"] != "present":
            warnings.append("Unresolved native input: " + item["role"])
            continue
        candidate = native_file(root, run_dir, item["path"], digest=item["md5"],
                                path_base=item.get("path_base") or path_base,
                                allow_external=item["role"] in REFERENCE_ROLES,
                                label="External reference" if item["role"] in REFERENCE_ROLES else "Native input")
        if not candidate.is_relative_to(root):
            # Installed annotation resources are dependencies, not project
            # source artifacts. Their original location remains in run_inputs.
            warnings.append(f"Verified external reference {item['role']} (MD5 {item['md5']}); "
                            f"location retained in {relative(inputs_file)} row {row_number}, not copied/registered as a project artifact")
            continue
        path = local_file(root, candidate)
        if relative(path) not in seen:
            rows.append({"path": relative(path), "role": item["role"], "direction": "input"})
            seen.add(relative(path))
            if item["role"] in REFERENCE_ROLES:
                reference_paths.add(relative(path))
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError("Native run contains symlinks")
        if path.is_file():
            path = local_file(root, path)
            if relative(path) in seen:
                if relative(path) in reference_paths:
                    continue
                raise ValueError("An input is also inside the output run: " + relative(path))
            rows.append({"path": relative(path), "role": "native_result", "direction": "output"})
            seen.add(relative(path))
    if delivery:
        manifest = local_file(root, delivery / "MANIFEST.tsv")
        for item in read_rows(manifest, "\t"):
            source_id = item.get("source_run_id")
            if source_id not in source_roots:
                raise ValueError("Delivery source run is unknown; supply --parent-run-dir for the registered parent")
            destination = local_file(root, delivery / item["path"])
            source = local_file(root, source_roots[source_id] / item["source_path"])
            destination.relative_to(Path(os.path.abspath(delivery)))
            source.relative_to(Path(os.path.abspath(source_roots[source_id])))
            if checksum(destination) != item["md5"] or checksum(source) != item["md5"]:
                raise ValueError("Delivery/source byte mismatch: " + item["path"])
            if source_id != native["run_id"] and relative(source) not in seen:
                rows.append({"path": relative(source), "direction": "reference"})
                seen.add(relative(source))
            if relative(source) not in seen or relative(destination) in seen:
                raise ValueError("Delivery source is outside the native inventory or path is duplicated")
            rows.append({"path": relative(destination), "role": "delivery", "direction": "delivery",
                         "parent_paths": [relative(source)]})
            seen.add(relative(destination))
        # Navigation/manifest are delivery artifacts even when generated by
        # the exporter and consequently lacking a byte-identical native parent.
        for name in ("MANIFEST.tsv", "README.html"):
            path = local_file(root, delivery / name)
            if relative(path) not in seen:
                rows.append({"path": relative(path), "role": "delivery_index", "direction": "delivery",
                             "parent_paths": [relative(run_dir / "run_manifest.csv")]})
    for row in rows:
        row["sha256"] = checksum(local_file(root, root / row["path"]), "sha256")
    return {
        "run": {
            "run_id": native["run_id"], "analysis_id": native["run_id"],
            "implementation_status": "implemented", "execution_status": native["status"],
            "technical_validation_status": "not_assessed", "entry_point": entry_point,
            "config_path": relative(config), "config_sha256": checksum(config, "sha256"),
            "backend_revision": native["backend_revision"],
            "environment_ref": relative(runtime), "completed_at": native["completed_at"],
            "notes": "Mapped native provenance only; scientific readiness not assessed. " + "; ".join(warnings),
        },
        "artifacts": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--run", required=True, help="Project-relative native run")
    parser.add_argument("--entry-point", required=True,
                        help="Actual project-relative source or backend:rnaseq-templates/<runner path>")
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--delivery", help="Optional project-relative exported delivery")
    parser.add_argument("--parent-run-dir", help="Registered parent for a mixed parent/derivative delivery")
    parser.add_argument("--output", required=True, help="New project-relative JSON; parent must exist")
    args = parser.parse_args()
    try:
        if args.project.is_symlink():
            raise ValueError("Project root must not be a symlink")
        root = args.project.resolve(strict=True)
        document = build(root, root / args.run, args.entry_point,
                         root / args.delivery if args.delivery else None,
                         root / args.parent_run_dir if args.parent_run_dir else None)
        document["run"]["analysis_id"] = args.analysis_id
        output = root / args.output
        # Validate the parent without creating extra project directories.
        current = root
        for part in output.relative_to(root).parts:
            if part == "..":
                raise ValueError("Output parent traversal is not allowed")
            current = current / part
            if current.is_symlink():
                raise ValueError("Output contains a symlink")
        with output.open("x", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(json.dumps({"output": args.output, "artifacts": len(document["artifacts"]),
                          "scientific_readiness": "not_assessed"}))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
