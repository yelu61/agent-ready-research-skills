#!/usr/bin/env python3
"""Validate every self-contained skill package in the repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
FORBIDDEN_SKILL_DOCS = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def package_target(skill: Path, origin: Path, target: str) -> Path:
    """Resolve a bundled resource without following a dependency outside it."""
    path = (origin.parent / target).resolve()
    if not path.is_relative_to(skill.resolve()):
        raise ValueError("resource resolves outside its independently installable package")
    return path


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line}")
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def validate_skill(skill: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill.relative_to(ROOT)}: missing SKILL.md"]

    try:
        text = skill_file.read_text(encoding="utf-8")
        metadata = frontmatter(text)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"{skill.relative_to(ROOT)}/SKILL.md: {exc}"]

    if set(metadata) != {"name", "description"}:
        errors.append(
            f"{skill.relative_to(ROOT)}/SKILL.md: frontmatter must contain only "
            f"name and description; found {sorted(metadata)}"
        )
    name = metadata.get("name", "")
    if name != skill.name:
        errors.append(
            f"{skill.relative_to(ROOT)}: folder name does not match skill name {name!r}"
        )
    if not NAME_RE.fullmatch(name):
        errors.append(f"{skill.relative_to(ROOT)}: invalid hyphen-case skill name")
    if not metadata.get("description"):
        errors.append(f"{skill.relative_to(ROOT)}/SKILL.md: empty description")
    if len(text.splitlines()) > 500:
        errors.append(f"{skill.relative_to(ROOT)}/SKILL.md: exceeds 500 lines")

    for filename in sorted(FORBIDDEN_SKILL_DOCS):
        if (skill / filename).exists():
            errors.append(
                f"{skill.relative_to(ROOT)}/{filename}: repository documentation "
                "does not belong inside a skill package"
            )

    openai_yaml = skill / "agents" / "openai.yaml"
    if not openai_yaml.is_file():
        errors.append(f"{skill.relative_to(ROOT)}: missing agents/openai.yaml")
    else:
        interface = openai_yaml.read_text(encoding="utf-8")
        if f"${name}" not in interface:
            errors.append(
                f"{openai_yaml.relative_to(ROOT)}: default prompt should reference ${name}"
            )

    license_file = skill / "LICENSE"
    if not license_file.is_file():
        errors.append(f"{skill.relative_to(ROOT)}: missing standalone LICENSE")

    for resource in skill.rglob("*"):
        if resource.is_symlink():
            errors.append(f"{resource.relative_to(ROOT)}: skill packages must not contain symlinks")
    for markdown in sorted(skill.rglob("*.md")):
        if not markdown.is_file():
            continue
        for match in LINK_RE.finditer(markdown.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            try:
                resolved = package_target(skill, markdown, target)
                if not resolved.exists():
                    raise ValueError("resource does not exist")
            except (OSError, ValueError) as exc:
                errors.append(f"{markdown.relative_to(ROOT)}: invalid bundled link {target!r}: {exc}")

    prompt_file = skill / "test-prompts.json"
    if prompt_file.exists():
        try:
            prompts = json.loads(prompt_file.read_text(encoding="utf-8"))
            if not isinstance(prompts, list) or not prompts:
                errors.append(
                    f"{prompt_file.relative_to(ROOT)}: expected a non-empty JSON list"
                )
            else:
                ids = set()
                for item in prompts:
                    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
                        errors.append(f"{prompt_file.relative_to(ROOT)}: each case needs a nonempty id")
                        continue
                    if item["id"] in ids:
                        errors.append(f"{prompt_file.relative_to(ROOT)}: duplicate case id {item['id']!r}")
                    ids.add(item["id"])
                    if not isinstance(item.get("prompt"), str) or not item["prompt"].strip():
                        errors.append(f"{prompt_file.relative_to(ROOT)}: case {item['id']} lacks a prompt")
                    if "material" in item:
                        try:
                            if not isinstance(item["material"], str):
                                raise ValueError("material must be a package-relative path")
                            if not package_target(skill, prompt_file, item["material"]).is_file():
                                raise ValueError("material file does not exist")
                        except (OSError, ValueError) as exc:
                            errors.append(f"{prompt_file.relative_to(ROOT)}: case {item['id']}: {exc}")
        except (json.JSONDecodeError, UnicodeError) as exc:
            errors.append(f"{prompt_file.relative_to(ROOT)}: {exc}")

    for script in sorted((skill / "scripts").rglob("*.py")):
        try:
            compile(
                script.read_text(encoding="utf-8"),
                str(script.relative_to(ROOT)),
                "exec",
            )
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{script.relative_to(ROOT)}: {exc}")

    return errors


def main() -> int:
    if not SKILLS_ROOT.is_dir():
        print("ERROR: missing skills/ directory", file=sys.stderr)
        return 1
    skills = sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())
    if not skills:
        print("ERROR: no skills found", file=sys.stderr)
        return 1

    errors: list[str] = []
    for skill in skills:
        errors.extend(validate_skill(skill))

    if errors:
        print(f"Validation failed with {len(errors)} issue(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(skills)} skill package(s):")
    for skill in skills:
        print(f"- {skill.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
