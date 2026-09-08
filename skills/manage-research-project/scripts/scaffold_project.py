#!/usr/bin/env python3
"""Safely scaffold missing project-memory files without overwriting content."""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import date
from pathlib import Path

from project_contracts import ContractError
from project_map import MAP_FILE, load_map, mapped_path, map_template
from exploratory_profile import EXPLORATORY_FILES


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "templates"

V2_COMMON_DIRS = [
    "docs",
    "data/raw",
    "data/processed",
    "data/metadata",
    "data/references",
    "workflows",
    "analysis/specs",
    "analysis/readiness",
    "results",
    "provenance",
]
RETROFIT_COMMON_DIRS = ["docs"]
RESEARCH_DIRS = ["analysis/specs", "analysis/readiness", "provenance"]
MANUSCRIPT_DIRS = ["manuscript", "manuscript/source_data"]

MINIMAL_FILES = {
    ".gitignore": ".gitignore",
    "AGENTS.md": "AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "README.md": "README.md",
    "docs/PROJECT_BRIEF.md": "docs/PROJECT_BRIEF.md",
    "docs/PROJECT_STATUS.md": "docs/PROJECT_STATUS.md",
    "docs/DECISION_LOG.md": "docs/DECISION_LOG.md",
    "docs/TODO.md": "docs/TODO.md",
    "docs/DATA_DICTIONARY.md": "docs/DATA_DICTIONARY.md",
    "docs/ANALYSIS_PLAN.md": "docs/ANALYSIS_PLAN.md",
    "docs/SESSION_HANDOFF.md": "docs/SESSION_HANDOFF.md",
}
V2_INIT_FILES = {
    "results/README.md": "results/README.md",
    "provenance/PROJECT_LAYOUT.json": "provenance/PROJECT_LAYOUT.json",
}
RESEARCH_FILES = {
    "docs/PIPELINE.md": "docs/PIPELINE.md",
    "docs/READINESS.md": "docs/READINESS.md",
    "docs/RESULTS_SUMMARY.md": "docs/RESULTS_SUMMARY.md",
    "docs/REPRODUCIBILITY.md": "docs/REPRODUCIBILITY.md",
    "provenance/ARTIFACTS.tsv": "provenance/ARTIFACTS.tsv",
    "provenance/RUNS.tsv": "provenance/RUNS.tsv",
}
MANUSCRIPT_FILES = {
    "manuscript/AUTHOR_QUERIES.md": "manuscript/AUTHOR_QUERIES.md",
    "manuscript/FIGURE_MANIFEST.tsv": "manuscript/FIGURE_MANIFEST.tsv",
    "manuscript/DELIVERABLE_SOURCE_MANIFEST.tsv": "manuscript/DELIVERABLE_SOURCE_MANIFEST.tsv",
}

ACCEPTED_EQUIVALENTS = {
    "docs/PIPELINE.md": ("PIPELINE.md",),
    "PIPELINE.md": ("docs/PIPELINE.md",),
}

DIRECTORY_OPEN_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)
SAFE_DIRFD_SUPPORTED = (
    all(
        function in os.supports_dir_fd
        for function in (os.open, os.mkdir, os.stat, os.unlink)
    )
    and os.stat in os.supports_follow_symlinks
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
)


def profile_spec(
    profile: str, *, mode: str = "init"
) -> tuple[list[str], dict[str, str]]:
    if profile == "exploratory":
        return [], {name: "../exploratory/" + name for name in EXPLORATORY_FILES}
    directories = list(V2_COMMON_DIRS if mode == "init" else RETROFIT_COMMON_DIRS)
    files = dict(MINIMAL_FILES)
    if mode == "init":
        files.update(V2_INIT_FILES)
    if profile in {"research", "manuscript"}:
        directories.extend(RESEARCH_DIRS)
        files.update(RESEARCH_FILES)
        if mode == "retrofit":
            files.pop("docs/PIPELINE.md")
            files["PIPELINE.md"] = "docs/PIPELINE.md"
    if profile == "manuscript":
        directories.extend(MANUSCRIPT_DIRS)
        files.update(MANUSCRIPT_FILES)
    return list(dict.fromkeys(directories)), files


def configured_profile_spec(profile, mode, mapping=None):
    directories, files = profile_spec(profile, mode=mode)
    if profile == "exploratory":
        if mapping is not None:
            raise ContractError("Exploratory notes preserve existing paths without a formal project map; choose research when mapping formal document roles.")
        return directories, files
    if mode == "retrofit" or mapping is not None:
        for name in ("README.md", "AGENTS.md", "CLAUDE.md"):
            files[name] = "legacy/" + name
    if mapping is not None:
        files.pop("provenance/PROJECT_LAYOUT.json", None)
        mapped_files = {}
        for name, template in files.items():
            destination = mapped_path(name, mapping)
            if destination in mapped_files:
                raise ContractError(f"Mapped scaffold files share a destination: {destination}")
            mapped_files[destination] = template
        files = mapped_files
        files[MAP_FILE] = "@project-map"
        directories = [mapping['docs_root']]
        if mode == "init":
            directories.extend(mapping['source_roots'] + mapping['raw_roots'] + [mapping['results_root']])
        if profile in {"research", "manuscript"}:
            directories.extend(RESEARCH_DIRS)
        if profile == "manuscript":
            directories.extend(MANUSCRIPT_DIRS)
        directories = [mapped_path(name, mapping) if name.startswith('docs/') else name for name in directories]
    return list(dict.fromkeys(directories)), files


def render(template: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def open_directory_tree(root_fd: int, relative: str) -> tuple[int, bool]:
    """Open/create a relative directory tree without following symlinks."""
    current_fd = os.dup(root_fd)
    leaf_created = False
    parts = Path(relative).parts
    try:
        for index, part in enumerate(parts):
            try:
                next_fd = os.open(part, DIRECTORY_OPEN_FLAGS, dir_fd=current_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o755, dir_fd=current_fd)
                    created = True
                except FileExistsError:
                    created = False
                next_fd = os.open(part, DIRECTORY_OPEN_FLAGS, dir_fd=current_fd)
                if index == len(parts) - 1:
                    leaf_created = created
            os.close(current_fd)
            current_fd = next_fd
        return current_fd, leaf_created
    except Exception:
        os.close(current_fd)
        raise


def write_file_exclusive(parent_fd: int, name: str, content: str) -> bool:
    """Create one regular file relative to a verified parent; never follow links."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_fd = os.open(name, flags, 0o644, dir_fd=parent_fd)
    except FileExistsError:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISREG(entry.st_mode):
            return False
        raise OSError("destination changed to a non-regular entry") from None
    try:
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            handle.write(content)
    except Exception:
        try:
            os.unlink(name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    return True


def plan_scaffold(target: Path, profile: str, mode: str, mapping=None) -> dict:
    directories, files = configured_profile_spec(profile, mode, mapping)
    conflicts: list[dict[str, str]] = []

    def accepted_equivalent(relative: str) -> str | None:
        if mapping is not None:
            return None
        for candidate in ACCEPTED_EQUIVALENTS.get(relative, ()):
            destination = target / candidate
            if destination.is_file() and not destination.is_symlink():
                return candidate
        return None

    def blocking_ancestor(relative: str) -> Path | None:
        current = target
        if current.is_symlink():
            return current
        for part in Path(relative).parts[:-1]:
            current = current / part
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                return current
        return None

    for relative in directories:
        destination = target / relative
        ancestor = blocking_ancestor(relative)
        if ancestor:
            conflicts.append(
                {
                    "path": relative,
                    "reason": f"parent path is not a directory: {ancestor}",
                }
            )
        elif destination.is_symlink():
            conflicts.append(
                {"path": relative, "reason": "directory path is a symlink"}
            )
        elif destination.exists() and not destination.is_dir():
            conflicts.append(
                {"path": relative, "reason": "directory path exists as a file"}
            )
    for relative in files:
        destination = target / relative
        ancestor = blocking_ancestor(relative)
        if ancestor:
            conflicts.append(
                {
                    "path": relative,
                    "reason": f"parent path is not a directory: {ancestor}",
                }
            )
        elif destination.is_symlink():
            conflicts.append({"path": relative, "reason": "file path is a symlink"})
        elif destination.exists() and not destination.is_file():
            conflicts.append(
                {"path": relative, "reason": "file path exists as a directory"}
            )

    return {
        "create_directories": [
            item
            for item in directories
            if not (target / item).exists() and not (target / item).is_symlink()
        ],
        "create_files": [
            item
            for item in files
            if not (target / item).exists()
            and not (target / item).is_symlink()
            and accepted_equivalent(item) is None
        ],
        "skip_existing_files": [
            item
            for item in files
            if (target / item).is_file() and not (target / item).is_symlink()
        ],
        "accepted_equivalent_files": [
            {"canonical": item, "existing": equivalent}
            for item in files
            if (equivalent := accepted_equivalent(item)) is not None
        ],
        "conflicts": conflicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create missing agent-ready research project files safely."
    )
    parser.add_argument("target", type=Path)
    parser.add_argument("--mode", choices=["auto", "init", "retrofit"], default="auto")
    parser.add_argument(
        "--profile", choices=["exploratory", "minimal", "research", "manuscript"], default="research"
    )
    parser.add_argument("--layout-map", type=Path, help="Explicit project-relative ownership mapping JSON; saved non-overwriting as PROJECT_MAP.json.")
    parser.add_argument("--project-name")
    parser.add_argument("--project-type")
    parser.add_argument("--objective")
    parser.add_argument("--stage")
    parser.add_argument(
        "--apply", action="store_true", help="Apply the displayed non-overwriting plan."
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    requested_target = args.target.expanduser()
    if requested_target.is_symlink():
        if args.json:
            print(
                json.dumps(
                    {
                        "target": str(requested_target),
                        "apply": args.apply,
                        "conflicts": [
                            {
                                "path": ".",
                                "reason": "project target is a symlink",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
            )
            return 1
        raise SystemExit(f"Project target must not be a symlink: {requested_target}")
    target = requested_target.resolve()
    existed = target.exists()
    if existed and not target.is_dir():
        raise SystemExit(f"Target exists and is not a directory: {target}")
    populated = existed and any(target.iterdir())
    selected_mode = (
        ("retrofit" if populated else "init") if args.mode == "auto" else args.mode
    )
    if selected_mode == "init" and populated:
        raise SystemExit(
            f"Refusing init on populated directory: {target}. Use --mode retrofit."
        )
    if selected_mode == "retrofit" and not existed:
        raise SystemExit(
            f"Refusing retrofit because the target does not exist: {target}. Use --mode init."
        )

    try:
        mapping = load_map(target, args.layout_map)
        plan = plan_scaffold(target, args.profile, selected_mode, mapping)
    except (ContractError, OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"target": str(target), "apply": args.apply,
                              "conflicts": [{"path": MAP_FILE, "reason": str(exc)}]}))
            return 1
        raise SystemExit(str(exc)) from exc
    fixed_v2 = mapping is None and selected_mode == 'init' and args.profile != 'exploratory'
    context = {
        "PROJECT_NAME": args.project_name or target.name or "TODO: project name",
        "PROJECT_TYPE": args.project_type or "TODO: project type / modality",
        "OBJECTIVE": args.objective or "TODO: main scientific question",
        "STAGE": args.stage
        or (
            "project initialized" if selected_mode == "init" else "TODO: current stage"
        ),
        "DATE": date.today().isoformat(),
        "SOURCE_ROOTS": ', '.join(mapping['source_roots']) if mapping else 'Inspect and retain existing source paths',
        "RAW_ROOTS": ', '.join(mapping['raw_roots']) if mapping else 'Inspect and retain original data paths (convention: data/raw)',
        "RUN_ROOT": mapping['run_root'] if mapping else ('analysis/runs' if fixed_v2 else 'TODO: verified existing run root'),
        "RESULTS_ROOT": mapping['results_root'] if mapping else ('results' if fixed_v2 else 'TODO: verified existing delivery root'),
        "SOURCE_POLICY": 'Keep authored code under workflows/<workflow_id>/.' if fixed_v2 else 'Retain authored code at its existing canonical paths; use the project map when present.',
        "ENTRY_POINT": 'workflows/<workflow_id>/scripts/<entrypoint>' if fixed_v2 else 'TODO: verified existing script or notebook entry point',
        "BACKEND_LOCK": 'workflows/<workflow_id>/backend.lock.json' if fixed_v2 else 'TODO: verified existing backend lock path',
    }
    if args.apply and not SAFE_DIRFD_SUPPORTED:
        plan["conflicts"].append(
            {
                "path": ".",
                "reason": (
                    "safe apply requires dir_fd, O_DIRECTORY and O_NOFOLLOW; "
                    "this platform supports dry-run only"
                ),
            }
        )
    report = {
        "target": str(target),
        "mode": selected_mode,
        "profile": args.profile,
        "apply": args.apply,
        **plan,
    }

    _, selected_files = configured_profile_spec(args.profile, selected_mode, mapping)
    rendered_files: dict[str, str] = {}
    for relative in plan["create_files"]:
        if selected_files[relative] == "@project-map":
            rendered_files[relative] = json.dumps(mapping, ensure_ascii=False, indent=2) + "\n"
            continue
        source = TEMPLATE_ROOT / selected_files[relative]
        if not source.is_file():
            raise SystemExit(f"Missing skill template: {source}")
        rendered_files[relative] = render(map_template(source.read_text(encoding="utf-8"), mapping), context)

    report["created_directories"] = []
    report["created_files"] = []
    report["concurrent_skip_files"] = []

    if args.apply and not plan["conflicts"]:
        target.mkdir(parents=True, exist_ok=True)
        try:
            root_fd = os.open(target, DIRECTORY_OPEN_FLAGS)
        except OSError as exc:
            plan["conflicts"].append(
                {"path": ".", "reason": f"cannot safely open project root: {exc}"}
            )
        else:
            try:
                for relative in plan["create_directories"]:
                    try:
                        directory_fd, created = open_directory_tree(root_fd, relative)
                        os.close(directory_fd)
                    except OSError as exc:
                        plan["conflicts"].append(
                            {
                                "path": relative,
                                "reason": f"directory path changed or is unsafe: {exc}",
                            }
                        )
                        break
                    if created:
                        report["created_directories"].append(relative)

                if not plan["conflicts"]:
                    for relative in plan["create_files"]:
                        parent = Path(relative).parent.as_posix()
                        try:
                            parent_fd, _ = open_directory_tree(root_fd, parent)
                        except OSError as exc:
                            plan["conflicts"].append(
                                {
                                    "path": relative,
                                    "reason": f"parent path changed or is unsafe: {exc}",
                                }
                            )
                            break
                        try:
                            created = write_file_exclusive(
                                parent_fd,
                                Path(relative).name,
                                rendered_files[relative],
                            )
                        except OSError as exc:
                            plan["conflicts"].append(
                                {
                                    "path": relative,
                                    "reason": f"destination changed or is unsafe: {exc}",
                                }
                            )
                            break
                        finally:
                            os.close(parent_fd)
                        if created:
                            report["created_files"].append(relative)
                        else:
                            report["concurrent_skip_files"].append(relative)
            finally:
                os.close(root_fd)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        action = "APPLIED" if args.apply else "DRY RUN"
        print(f"{action}: {selected_mode} / {args.profile} -> {target}")
        for key in (
            "create_directories",
            "create_files",
            "skip_existing_files",
            "accepted_equivalent_files",
            "conflicts",
        ):
            print(f"{key}: {len(plan[key])}")
            for item in plan[key]:
                print(f"  - {item}")
        if not args.apply:
            print(
                "No files were changed. Re-run with --apply after reviewing this plan."
            )
    return 1 if plan["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
