"""Explicit existing-layout mapping; does not migrate files or grant readiness."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
import unicodedata

from project_contracts import ContractError, load_json_object, portable_project_relative, resolve_project_relative

MAP_FILE = "PROJECT_MAP.json"
SCHEMA = "research-project-map/v1"
DOCUMENT_NAMES = {
    "PROJECT_BRIEF.md", "PROJECT_STATUS.md", "DECISION_LOG.md", "TODO.md",
    "DATA_DICTIONARY.md", "ANALYSIS_PLAN.md", "SESSION_HANDOFF.md", "PIPELINE.md",
    "READINESS.md", "RESULTS_SUMMARY.md", "REPRODUCIBILITY.md", "DATA_GOVERNANCE.md",
}
REQUIRED = {"schema_version", "docs_root", "source_roots", "raw_roots", "run_root", "results_root"}
RESERVED = (
    "provenance", "analysis/specs", "analysis/readiness", "PROJECT_MAP.json",
    "AGENTS.md", "CLAUDE.md", "README.md", "manuscript/AUTHOR_QUERIES.md",
    "manuscript/FIGURE_MANIFEST.tsv", "manuscript/DELIVERABLE_SOURCE_MANIFEST.tsv",
)


def path_key(value):
    """Reject aliases even when a project moves to a case-insensitive volume."""
    return unicodedata.normalize("NFC", value).casefold()


def overlaps(left, right):
    a, b = PurePosixPath(path_key(left)), PurePosixPath(path_key(right))
    return a == b or a in b.parents or b in a.parents


def validate_map(document, root):
    if not isinstance(document, dict) or set(document) - REQUIRED - {"documents"} or not REQUIRED <= set(document):
        raise ContractError("Project map needs schema_version, docs_root, source_roots, raw_roots, run_root, results_root; only documents is optional.")
    if document["schema_version"] != SCHEMA:
        raise ContractError(f"Project map schema_version must be {SCHEMA}.")
    roles = []

    def local_path(value):
        relative = portable_project_relative(value)
        if relative != value or any(part.startswith('.') for part in PurePosixPath(relative).parts):
            raise ContractError("Mapped paths must be normalized, non-hidden project-relative paths.")
        resolve_project_relative(root, relative)
        return relative

    for key in ("docs_root", "run_root", "results_root"):
        roles.append((key, local_path(document[key])))
    for key in ("source_roots", "raw_roots"):
        values = document[key]
        if not isinstance(values, list) or not values:
            raise ContractError(f"{key} must be a nonempty list; do not guess unknown roots.")
        for value in values:
            roles.append((key, local_path(value)))
    for i, (role, path) in enumerate(roles):
        for other_role, other in roles[i + 1:]:
            if overlaps(path, other):
                raise ContractError(f"Mapped ownership overlaps: {role}={path}, {other_role}={other}.")
        for reserved in RESERVED:
            if overlaps(path, reserved):
                raise ContractError(f"Mapped root overlaps reserved control path: {path} / {reserved}.")
        candidate = root / path
        if candidate.exists() and not candidate.is_dir():
            raise ContractError(f"Mapped directory is not a directory: {path}.")
    documents = document.get("documents", {})
    if not isinstance(documents, dict) or set(documents) - {f"docs/{name}" for name in DOCUMENT_NAMES}:
        raise ContractError("documents maps known docs/<DOCUMENT>.md roles to local files.")
    targets = set()
    for name in DOCUMENT_NAMES:
        role = f"docs/{name}"
        path = local_path(documents.get(role, f'{document["docs_root"]}/{name}'))
        if any(overlaps(path, target) for target in targets):
            raise ContractError(f"Distinct document roles overlap: {path}; use exploratory for a combined notebook.")
        targets.add(path)
        for directory_role, directory in roles:
            if directory_role != "docs_root" and overlaps(path, directory):
                raise ContractError(f"Document {path} overlaps {directory_role}={directory}.")
        if any(overlaps(path, reserved) for reserved in RESERVED):
            raise ContractError(f"Document mapping overlaps a reserved control path: {path}.")
        if path_key(path) == path_key(document['docs_root']) or PurePosixPath(path_key(path)) in PurePosixPath(path_key(document['docs_root'])).parents:
            raise ContractError(f"Document mapping shadows its document directory: {path}.")
        if (root / path).exists() and not (root / path).is_file():
            raise ContractError(f"Mapped document is not a regular file: {path}.")
    return document


def load_map(root, supplied=None):
    saved = root / MAP_FILE
    if supplied is None and not saved.exists() and not saved.is_symlink():
        return None
    path = Path(supplied) if supplied is not None else saved
    if path.is_symlink() or not path.is_file():
        raise ContractError("Project map must be a regular JSON file, not a symlink.")
    if supplied is None:
        resolve_project_relative(root, MAP_FILE, must_exist=True)
    document = validate_map(load_json_object(path), root)
    if supplied is not None and (saved.exists() or saved.is_symlink()):
        if saved.is_symlink() or load_json_object(saved) != document:
            raise ContractError("Saved PROJECT_MAP.json differs; do not silently replace a project's mapping.")
    if (root / 'provenance/PROJECT_LAYOUT.json').exists() or (root / 'provenance/PROJECT_LAYOUT.json').is_symlink():
        raise ContractError("PROJECT_MAP.json and fixed layout v2 cannot both own a project. Review a layout migration explicitly.")
    return document


def mapped_path(relative, document):
    if document is None:
        return relative
    if relative.startswith('docs/'):
        return document.get('documents', {}).get(relative, document['docs_root'] + relative[4:])
    if relative == 'PIPELINE.md':
        return mapped_path('docs/PIPELINE.md', document)
    if relative.startswith('results/'):
        return document['results_root'] + relative[7:]
    return relative


def map_template(text, document):
    if document is None:
        return text
    substitutions = {f'docs/{name}': mapped_path(f'docs/{name}', document) for name in DOCUMENT_NAMES}
    substitutions.update({'analysis/runs': document['run_root'], 'results/': document['results_root'] + '/'})
    pattern = '|'.join(re.escape(k) for k in sorted(substitutions, key=len, reverse=True))
    return re.sub(pattern, lambda match: substitutions[match.group()], text)


def audit_map(root, document):
    findings = []
    for role in ('source_roots', 'raw_roots'):
        for relative in document[role]:
            if not (root / relative).is_dir():
                findings.append({'level': 'info', 'code': 'mapped-root-absent', 'path': relative,
                                 'message': f'{role} is declared but absent; mapping is not evidence of data or execution.'})
    return findings
