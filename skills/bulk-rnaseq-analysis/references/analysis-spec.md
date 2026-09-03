# BulkAnalysisSpec and Preflight Gating

The router (`scripts/backend_router.py`) answers *which backend*. Preflight
(`scripts/preflight.py`) answers *whether the claim you want to make is
allowed*. Program success is not scientific validity: a run that finishes can
still support only a weaker claim than intended.

## Claim classes

`descriptive` < `exploratory` < `confirmatory` < `predictive` < `causal` < `clinical`

Every spec declares the strongest claim it intends (`claim_class`).
`assets/backend-capabilities.json` caps each (backend, task) pair at a maximum
claim class, with evidence and a minimal fix for lifting the cap. Asking for
more than the cap exits 3 (blocked) with a stable gate ID.

## Spec v1

Schema: `assets/schemas/bulk-analysis-spec-v1.schema.json`. Required fields:

- `question`, `claim_class`, `backend`, `task`
- `input_scale` (`raw-counts`, `tpm`, `log-tpm`, `vst`, `rlog`, `normalized`)
- `experimental_unit` (`sample` / `patient` / `cell`)
- `design` (`formula`, `contrast`, `batch`, `pairing`, `time`, `interaction`)
- `inputs` (named files; sha256 computed by preflight)
- `split_policy` (required in practice for predictive claims:
  `level: patient`, `locked_features`, `locked_transform`, `locked_cutoff`)

## Workflow

```bash
python3 scripts/preflight.py check --spec spec.json --backend-revision <git-rev>
# -> readiness record <spec>.readiness.json, exit 0 ready / 3 blocked

python3 scripts/preflight.py verify --spec spec.json --readiness spec.readiness.json
# -> exit 4 if spec, any input, or the backend revision changed
```

A readiness record is invalidated by any drift — never reuse an old verdict
after editing the spec, an input, or the backend.

## Current capability caps (2026-09-03)

| Backend / task | Max claim | Note |
| --- | --- | --- |
| rnaseq-templates deg, limma-voom | confirmatory | ID-aware alignment, integer-count gate |
| rnaseq-templates time-course | confirmatory, interaction BLOCKED | additive designs only |
| rnaseq-templates gsva / tme / wgcna / survival | exploratory | secondary or discovery analyses |
| tcga-toolkit deg | confirmatory | integer gate, patient dedup, covariates |
| tcga-toolkit gtex-compare | descriptive | no cross-dataset normalization |
| tcga-toolkit prognostic-model | exploratory | nested CV + calibration still missing |
| tcga-toolkit external-validation | predictive only with locked features/transform/cutoff | pass `model_meta_file` |
| tcga-toolkit survival | exploratory | patient dedup + PH check reported |
