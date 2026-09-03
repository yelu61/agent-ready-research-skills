#!/usr/bin/env python3
"""Safely scaffold missing project-memory files without overwriting content."""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import date
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "templates"

COMMON_DIRS = [
    "docs",
    "data/raw",
    "data/processed",
    "data/metadata",
    "notebooks",
    "scripts/R",
    "scripts/python",
    "results/tables",
    "results/figures",
    "results/intermediate",
    "results/reports",
]
RESEARCH_DIRS = ["prompts", "analysis/specs", "analysis/readiness", "provenance"]
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
RESEARCH_FILES = {
    "PIPELINE.md": "PIPELINE.md",
    "docs/READINESS.md": "docs/READINESS.md",
    "docs/RESULTS_SUMMARY.md": "docs/RESULTS_SUMMARY.md",
    "docs/REPRODUCIBILITY.md": "docs/REPRODUCIBILITY.md",
    "provenance/ARTIFACTS.tsv": "provenance/ARTIFACTS.tsv",
    "provenance/RUNS.tsv": "provenance/RUNS.tsv",
    "prompts/notebook_audit.md": "prompts/notebook_audit.md",
    "prompts/figure_story.md": "prompts/figure_story.md",
    "prompts/result_interpretation.md": "prompts/result_interpretation.md",
}
MANUSCRIPT_FILES = {
    "manuscript/AUTHOR_QUERIES.md": "manuscript/AUTHOR_QUERIES.md",
    "manuscript/FIGURE_MANIFEST.tsv": "manuscript/FIGURE_MANIFEST.tsv",
    "manuscript/DELIVERABLE_SOURCE_MANIFEST.tsv": "manuscript/DELIVERABLE_SOURCE_MANIFEST.tsv",
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


def profile_spec(profile: str) -> tuple[list[str], dict[str, str]]:
    directories = list(COMMON_DIRS)
    files = dict(MINIMAL_FILES)
    if profile in {"research", "manuscript"}:
        directories.extend(RESEARCH_DIRS)
        files.update(RESEARCH_FILES)
    if profile == "manuscript":
        directories.extend(MANUSCRIPT_DIRS)
        files.update(MANUSCRIPT_FILES)
    return directories, files


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


def plan_scaffold(target: Path, profile: str) -> dict:
    directories, files = profile_spec(profile)
    conflicts: list[dict[str, str]] = []

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
            if not (target / item).exists() and not (target / item).is_symlink()
        ],
        "skip_existing_files": [
            item
            for item in files
            if (target / item).is_file() and not (target / item).is_symlink()
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
        "--profile", choices=["minimal", "research", "manuscript"], default="research"
    )
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

    context = {
        "PROJECT_NAME": args.project_name or target.name or "TODO: project name",
        "PROJECT_TYPE": args.project_type or "TODO: project type / modality",
        "OBJECTIVE": args.objective or "TODO: main scientific question",
        "STAGE": args.stage
        or (
            "project initialized" if selected_mode == "init" else "TODO: current stage"
        ),
        "DATE": date.today().isoformat(),
    }
    plan = plan_scaffold(target, args.profile)
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

    _, selected_files = profile_spec(args.profile)
    rendered_files: dict[str, str] = {}
    for relative in plan["create_files"]:
        source = TEMPLATE_ROOT / selected_files[relative]
        if not source.is_file():
            raise SystemExit(f"Missing skill template: {source}")
        rendered_files[relative] = render(source.read_text(encoding="utf-8"), context)

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
