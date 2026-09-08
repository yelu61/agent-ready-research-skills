# Runtime and Audit Limits

Core planning, interpretation and manual audit need no Python dependency.
The optional h5ad inspector needs a working analysis environment with AnnData,
NumPy, SciPy and pandas (and AnnData's HDF5 dependencies). The bundled handoff
checker uses only the Python standard library. Resolve script paths relative
to this installed skill; no sibling skill, source checkout or scLucid is needed.

## Tested boundary

Synthetic regressions on 2026-09-08 used Python 3.11.4, AnnData 0.11.3,
NumPy 2.0.2, SciPy 1.15.1, pandas 2.2.2 and h5py 3.13.0. This is one observed
working combination, not a claim that all versions work or a recommendation to
downgrade an existing environment. Python-only helpers target Python 3.9+;
the h5ad reader must also meet its installed AnnData version's requirements.
Use an existing analysis environment and check its imports. Do not silently
install or upgrade packages. No full scRNA pipeline or performance benchmark
has been run as part of these helper regressions.

## What the inspector establishes

- It checks identifiers, candidate metadata columns, missing labels, count-layer
  presence, sampled matrix values, and the observed batch–condition graph.
- With `--contrast A B`, it checks the condition contrast in an additive
  categorical `batch + condition` model. Conditions in different graph
  components are not estimable after batch adjustment; conditions within the
  same component can be estimable even when the whole design is rank deficient.
- No batch key or absent requested levels means unknown, not no confounding.
  Complete-case connectivity does not resolve missingness, unmeasured batch,
  paired/repeated measures, additional covariates, interaction terms, sufficient
  independent donors or causal identification. Inspect the full model separately.
- Numeric summaries use up to three 128×256 blocks (start, middle, end), including
  implicit zeros in both sparse and dense matrices. Blocks may overlap; counts
  refer to sampled entries, not a count of unique anomalies across the file.
  Unsampled values remain unknown. Integer resemblance never proves raw-count
  provenance. Fractional estimates trigger review of method-specific input
  requirements; do not automatically round abundance/corrected estimates.
- `backed='r'` does not make every layer/annotation lazy. Large multilayer files
  may require substantial RAM. The bounded value sample is not a peak-memory
  guarantee; use an appropriate environment or a specialist on-disk reader.

## Output and failure behavior

Stdout is the default. `--output report.json` atomically creates a new report.
Existing reports need explicit `--overwrite-output`. Input paths and their
symlink/hard-link aliases are rejected; output symlinks are rejected. The h5ad
handle closes even if inspection or report generation fails.

Exit 0 means a report was generated, including reports containing BLOCKED
issues. Exit 2 means invalid input/output arguments; 3 means the analysis
dependency could not import; 4 means inspection/report generation failed.
Always inspect issues and scope; no exit code is an overall scientific READY.

## Verification scope

Repository tests exercise helper behavior with synthetic inputs, including
read-only protection, disconnected contrasts, missing metadata and matrix
edge cases. Numerical tests skip with the import error when the environment
cannot load AnnData; standard-library safety/connectivity tests still run.
The prose cases in evaluation-cases are evaluation designs, not completed
independent model evaluations. Report model behavior only after recording an
actual isolated run with inputs, outputs, model version and reviewer criteria.
