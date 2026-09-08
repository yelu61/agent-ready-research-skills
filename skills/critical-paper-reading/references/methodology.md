# Methodology, sources and standalone use

Last checked: 2026-09-08. These are original workflow instructions informed by
the linked sources; no article text, figures or publisher supplements are bundled.

| Rule | Primary or official source | Scope and limitation |
|---|---|---|
| Define causal estimands and identification assumptions separately from prediction/replication | [Hernán and Robins, author resource](https://miguelhernan.org/whatifbook) | Exchangeability, positivity, consistency and timing must fit the actual design. |
| Respect biological units in condition-level scRNA inference | [Squair et al., 2021](https://doi.org/10.1038/s41467-021-25960-2) | Pseudobulk does not create missing donors or remove design confounding; appropriate hierarchical methods remain possible. |
| Review reporting and scientific validity separately | [CONSORT 2025](https://doi.org/10.1136/bmj-2024-081123) | Reporting completeness is not a low-bias certificate. Use the applicable guideline/extension for the study type. |
| Distinguish treatment-effect prediction from outcome prediction | [FDA–NIH BEST](https://www.ncbi.nlm.nih.gov/books/NBK402283/) | A predictor in one treatment arm does not establish differential treatment benefit. |

For a material revision, recheck affected rules against primary sources and
record the scope and access limits. Updating a date alone is not a review.
Article version/correction status, novelty and current baselines require a
task-specific lookup. Source availability is not proof that a source supports
the claim; inspect the relevant methods/results before citing it.

## Domain-specific checks

- Single-cell/spatial: patients, specimens, captures and cells are different
  units. Review patient uncertainty, composition, spatial dependence and donor
  splits. Random cell partitions do not create new replicates.
- Mechanism: inspect each causal link, reagent specificity, dose/time, toxicity,
  off-target and rescue controls. Direct negative results can contradict a claim.
- Prediction: trace feature selection and fitting within training folds, patient
  overlap, tuning, locked preprocessing and calibration. Discrimination is not
  clinical utility.
- Clinical: inspect population, time zero, endpoint, censoring, analysis set and
  deviations. Do not substitute reporting checklists for bias assessment.

## Runtime and optional adapters

Supplied-text review requires only a capable agent client, no Python packages,
other skills, scLucid or network. Use available file/browser/PDF tools for
retrieval or figure inspection; if absent, complete a bounded review of what
was supplied. Literature-search, statistical-review and scientific-reasoning
skills are optional extensions. Without them, apply the checks here directly.
Only hand off a new research-design task if requested; do not automatically
produce a second full report.

## Evaluation

`test-prompts.json` contains synthetic materials and rubrics, not model pass
records. Give the evaluator only the prompt and material; record its actual
response and separately judge meaning and source anchors against the rubric.
Include both forbidden overclaims and justified narrow claims. No software
installation or external article retrieval is needed for these fixtures.
