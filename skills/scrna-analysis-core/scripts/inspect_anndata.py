#!/usr/bin/env python3
"""Bounded, read-only AnnData structural audit; not a complete statistical review."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

KEY_CANDIDATES = {
    "sample": ("sample_id", "sampleID", "sample", "donor", "patient", "orig.ident", "orig_ident"),
    "batch": ("batch", "batch_id", "library", "lane", "chemistry", "sequencing_run"),
    "condition": ("condition", "treatment", "group", "disease", "response", "timepoint"),
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    for role in KEY_CANDIDATES:
        parser.add_argument(f"--{role}-key")
    parser.add_argument("--contrast", nargs=2, metavar=("CONDITION_A", "CONDITION_B"),
                        help="Check A minus B in the additive batch + condition model only")
    parser.add_argument("--output", type=Path, help="Optional .json report; stdout by default")
    parser.add_argument("--overwrite-output", action="store_true", help="Replace an existing JSON report")
    return parser.parse_args(argv)


def validate_output(source, output, overwrite=False):
    if source.resolve() == output.resolve() or (output.exists() and source.samefile(output)):
        raise ValueError("Output must not be the input or its symlink/hard-link alias.")
    if output.is_symlink():
        raise ValueError("Output must not be a symbolic link.")
    if output.suffix.lower() != ".json":
        raise ValueError("Output must have a .json extension.")
    if output.exists() and not overwrite:
        raise FileExistsError("Output exists; use --overwrite-output to replace this JSON report.")
    if not output.parent.is_dir():
        raise ValueError("Output parent directory does not exist.")


def write_report(source, output, payload, overwrite=False):
    """Atomic report publication; exclusive creation is the default."""
    validate_output(source, output, overwrite)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".anndata-report-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        validate_output(source, output, overwrite)
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)  # Fails if a concurrent writer created the destination.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def first_present(columns, preferred, candidates):
    if preferred:
        return preferred if preferred in columns else None
    return next((key for key in candidates if key in columns), None)


def design_connectivity(pairs, contrast=None):
    """Exact connectivity criterion for contrasts in an additive two-factor model.

    Does not establish replication, pairing/covariate adjustment, or causality.
    """
    graph = {}
    edges = sorted(set((str(batch), str(condition)) for batch, condition in pairs))
    for batch, condition in edges:
        a, b = ("batch", batch), ("condition", condition)
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    components, membership = [], {}
    for node in sorted(graph):
        if node in membership:
            continue
        index, stack, nodes = len(components), [node], []
        membership[node] = index
        while stack:
            current = stack.pop()
            nodes.append(current)
            for neighbor in sorted(graph[current]):
                if neighbor not in membership:
                    membership[neighbor] = index
                    stack.append(neighbor)
        components.append({"batches": sorted(n[1] for n in nodes if n[0] == "batch"),
                           "conditions": sorted(n[1] for n in nodes if n[0] == "condition")})
    batches, conditions = {b for b, _ in edges}, {c for _, c in edges}
    report = {
        "model_scope": "additive categorical batch + condition; no other covariates or interactions",
        "observed_batch_condition_pairs": [list(edge) for edge in edges],
        "connected_components": components, "n_components": len(components),
        "batch_condition_confounded": len(components) > 1 if components else None,
        "additive_design_rank": len(batches) + len(conditions) - len(components) if components else None,
        "additive_design_columns": len(batches) + len(conditions) - 1 if components else None,
        "limitation": "Within-component contrasts can be estimable in a rank-deficient design. Replication and the complete requested model still need review.",
    }
    if contrast:
        a, b = map(str, contrast)
        present = a in conditions and b in conditions
        estimable = membership[("condition", a)] == membership[("condition", b)] if present else None
        report["contrast"] = {"condition_a": a, "condition_b": b, "estimable": estimable,
            "reason": ("Requested condition absent from complete batch-condition metadata." if not present
                       else "Same connected component." if estimable
                       else "Disconnected components; the batch-adjusted contrast is not identifiable.")}
    return report


def matrix_summary(matrix):
    if matrix is None:
        return {"type": "NoneType", "sampling_note": "No matrix is present."}
    result = {"type": type(matrix).__name__, "shape": list(map(int, matrix.shape)),
              "dtype": str(getattr(matrix, "dtype", "unknown")), "sample_integer_like_fraction": None}
    try:
        import numpy as np
        from scipy import sparse
        nr, nc = matrix.shape
        height, width = min(128, nr), min(256, nc)
        starts = sorted({(0, 0), (max(0, (nr-height)//2), max(0, (nc-width)//2)),
                         (max(0, nr-height), max(0, nc-width))})
        samples, blocks = [], []
        for row, col in starts:
            block = matrix[row:row+height, col:col+width]
            if hasattr(block, "to_memory"):
                block = block.to_memory()
            # Bounded densification provides the same denominator for sparse and dense data.
            samples.append(block.toarray().ravel() if sparse.issparse(block) else np.asarray(block).ravel())
            blocks.append({"row_start": row, "row_stop": row+height,
                           "column_start": col, "column_stop": col+width})
        values = np.concatenate(samples)
        finite = np.isfinite(values)
        clean = values[finite]
        result.update({"sampled_blocks": blocks, "sampled_value_count": int(values.size),
            "sampling_scope": "At most three 128x256 blocks. Overlap may repeat entries. Includes implicit zeros. Unsampled values are unknown; this is not count provenance.",
            "nonfinite_count": int((~finite).sum()), "negative_count": int((clean < 0).sum()),
            "integer_denominator": "finite sampled entries, including zeros"})
        if clean.size:
            result["sample_integer_like_fraction"] = float(np.mean(np.isclose(clean, np.round(clean), atol=1e-6, rtol=0)))
    except Exception as exc:
        result["sampling_note"] = f"Could not sample values: {type(exc).__name__}: {exc}"
    return result


def build_report(adata, args):
    import pandas as pd
    columns, issues, resolved = list(map(str, adata.obs.columns)), [], {}

    def issue(severity, code, message):
        issues.append({"severity": severity, "code": code, "issue": message})

    for role, candidates in KEY_CANDIDATES.items():
        preferred = getattr(args, f"{role}_key")
        found = [key for key in candidates if key in columns]
        resolved[role] = first_present(columns, preferred, candidates)
        if preferred and resolved[role] is None:
            issue("BLOCKED", "requested_key_absent", f"Requested {role} key {preferred!r} is absent.")
        elif not preferred and len(found) > 1:
            issue("REVIEW", "ambiguous_metadata_key", f"Multiple {role} candidates {found}; selected {resolved[role]!r}. Confirm with --{role}-key.")
    for axis in ("obs", "var"):
        if not getattr(adata, f"{axis}_names").is_unique:
            issue("BLOCKED", "duplicate_identifiers", f"{axis}_names are not unique.")
    matrices = {"X": matrix_summary(adata.X)}
    matrices.update({f"layers/{name}": matrix_summary(adata.layers[name]) for name in adata.layers})
    if "counts" not in adata.layers:
        issue("REVIEW", "counts_source_unknown", "No layers['counts']; verify the authoritative count source, which may be elsewhere.")
    else:
        counts = matrices["layers/counts"]
        if counts.get("nonfinite_count", 0) or counts.get("negative_count", 0):
            issue("BLOCKED", "invalid_count_values", "Sampled counts have nonfinite/negative values; count-based modeling requires a valid source.")
        if counts.get("sample_integer_like_fraction") is not None and counts["sample_integer_like_fraction"] < 1:
            issue("REVIEW", "fractional_counts", "Fractional counts: verify quantification/correction provenance and model input requirements; do not round automatically.")
        if counts.get("sampling_note") or counts.get("sampled_value_count", 0) == 0:
            issue("REVIEW", "counts_not_sampled", "Counts could not be sampled or contain no entries.")
    if adata.n_obs == 0 or adata.n_vars == 0:
        issue("BLOCKED", "empty_object", "No observations or no features.")
    design, clean = {"resolved_keys": resolved, "metadata_missing": {}}, {}
    plurals = {"sample": "samples", "batch": "batches", "condition": "conditions"}
    for role, key in resolved.items():
        if key:
            series = adata.obs[key].astype("string").str.strip().replace("", pd.NA)
            clean[role] = series
            missing = int(series.isna().sum())
            design["metadata_missing"][role] = {"count": missing, "fraction": missing/len(series) if len(series) else None}
            design[f"n_{plurals[role]}"] = int(series.dropna().nunique())
            if missing:
                issue("BLOCKED" if missing == len(series) else "REVIEW", "missing_metadata_values",
                      f"{role}: {missing}/{len(series)} missing labels; design summaries omit these entries.")
    if resolved["sample"] is None:
        issue("REVIEW", "sample_source_unknown", "No sample key; sample-level inference is not auditable. Single-library exploration may still be possible.")
    if "sample" in clean and "condition" in clean:
        mapping = pd.DataFrame({"sample": clean["sample"], "condition": clean["condition"]}).dropna().drop_duplicates()
        design["samples_per_condition"] = {str(group): int(frame["sample"].nunique()) for group, frame in mapping.groupby("condition", observed=True)}
        if len(design["samples_per_condition"]) > 1 and any(n < 2 for n in design["samples_per_condition"].values()):
            issue("REVIEW", "limited_replication", "A condition has fewer than two resolved samples; cell counts do not supply independent replication. Check the experimental unit and intended claim.")
        design["samples_in_multiple_conditions"] = int((mapping.groupby("sample", observed=True)["condition"].nunique() > 1).sum())
    if "batch" in clean and "condition" in clean:
        table = pd.DataFrame({"batch": clean["batch"], "condition": clean["condition"]}).dropna().drop_duplicates()
        design.update(design_connectivity(table.itertuples(index=False, name=None), args.contrast))
        if design["batch_condition_confounded"]:
            severity = "BLOCKED" if args.contrast and design["contrast"]["estimable"] is False else "REVIEW"
            issue(severity, "disconnected_design", "Batch-condition graph is disconnected. Cross-component contrasts are not identifiable; within-component contrasts may be estimable.")
    else:
        design["batch_condition_confounded"] = None
        if args.contrast:
            design["contrast"] = {"condition_a": args.contrast[0], "condition_b": args.contrast[1], "estimable": None,
                                  "reason": "Batch or condition metadata unavailable; additive model not checked."}
    if args.contrast and design["contrast"]["estimable"] is None:
        issue("REVIEW", "contrast_not_checked", design["contrast"]["reason"])
    return {"input": str(args.input.resolve()), "read_only": True,
        "audit_scope": "Bounded matrix sampling and additive batch-condition metadata. No overall READY verdict; no complete design, biological, or inferential validation.",
        "memory_note": "backed='r' does not ensure lazy loading of all layers/annotations; large multilayer files may need substantial RAM.",
        "shape": {"n_obs": int(adata.n_obs), "n_vars": int(adata.n_vars)},
        "names_unique": {"obs": bool(adata.obs_names.is_unique), "var": bool(adata.var_names.is_unique)},
        "obs_columns": columns, "var_columns": list(map(str, adata.var.columns)),
        "layers": list(map(str, adata.layers)), "obsm": list(map(str, adata.obsm)), "uns": list(map(str, adata.uns)),
        "raw_present": adata.raw is not None, "matrices": matrices, "design": design, "issues": issues}


def main(argv=None):
    args = parse_args(argv)
    try:
        if not args.input.is_file() or args.input.suffix.lower() != ".h5ad":
            raise ValueError("Input must be an existing .h5ad file.")
        if args.output:
            validate_output(args.input, args.output, args.overwrite_output)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        import anndata as ad
    except (ImportError, OSError) as exc:
        print(f"A working anndata analysis environment is required: {exc}", file=sys.stderr)
        return 3
    adata = None
    try:
        try:
            adata = ad.read_h5ad(args.input, backed="r")
            report = build_report(adata, args)
        finally:
            if adata is not None and getattr(adata, "file", None) is not None:
                adata.file.close()
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            write_report(args.input, args.output, payload, args.overwrite_output)
        else:
            print(payload)
    except Exception as exc:
        print(f"Inspection failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 4
    return 0  # Generated a report; this does not mean the analysis is READY.


if __name__ == "__main__":
    raise SystemExit(main())
