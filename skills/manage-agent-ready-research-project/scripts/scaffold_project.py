#!/usr/bin/env python3
"""Safely scaffold missing project-memory files without overwriting content."""

from __future__ import annotations

import argparse
import json
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
RESEARCH_DIRS = ["prompts"]
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
    "docs/RESULTS_SUMMARY.md": "docs/RESULTS_SUMMARY.md",
    "docs/REPRODUCIBILITY.md": "docs/REPRODUCIBILITY.md",
    "prompts/notebook_audit.md": "prompts/notebook_audit.md",
    "prompts/figure_story.md": "prompts/figure_story.md",
    "prompts/result_interpretation.md": "prompts/result_interpretation.md",
}
MANUSCRIPT_FILES = {
    "manuscript/AUTHOR_QUERIES.md": "manuscript/AUTHOR_QUERIES.md",
    "manuscript/FIGURE_MANIFEST.tsv": "manuscript/FIGURE_MANIFEST.tsv",
    "manuscript/SOURCE_MANIFEST.tsv": "manuscript/SOURCE_MANIFEST.tsv",
}


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


def plan_scaffold(target: Path, profile: str) -> dict:
    directories, files = profile_spec(profile)
    return {
        "create_directories": [
            item for item in directories if not (target / item).exists()
        ],
        "create_files": [
            item for item in files if not (target / item).exists()
        ],
        "skip_existing_files": [
            item for item in files if (target / item).exists()
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create missing agent-ready research project files safely."
    )
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--mode", choices=["auto", "init", "retrofit"], default="auto"
    )
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

    target = args.target.expanduser().resolve()
    existed = target.exists()
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
        "STAGE": args.stage or ("project initialized" if selected_mode == "init" else "TODO: current stage"),
        "DATE": date.today().isoformat(),
    }
    plan = plan_scaffold(target, args.profile)
    report = {
        "target": str(target),
        "mode": selected_mode,
        "profile": args.profile,
        "apply": args.apply,
        **plan,
    }

    if args.apply:
        target.mkdir(parents=True, exist_ok=True)
        for relative in plan["create_directories"]:
            (target / relative).mkdir(parents=True, exist_ok=True)
        _, files = profile_spec(args.profile)
        for relative in plan["create_files"]:
            source = TEMPLATE_ROOT / files[relative]
            if not source.is_file():
                raise SystemExit(f"Missing skill template: {source}")
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                render(source.read_text(encoding="utf-8"), context),
                encoding="utf-8",
            )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        action = "APPLIED" if args.apply else "DRY RUN"
        print(f"{action}: {selected_mode} / {args.profile} -> {target}")
        for key in ("create_directories", "create_files", "skip_existing_files"):
            print(f"{key}: {len(plan[key])}")
            for item in plan[key]:
                print(f"  - {item}")
        if not args.apply:
            print("No files were changed. Re-run with --apply after reviewing this plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
