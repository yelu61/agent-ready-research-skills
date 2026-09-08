# Statistical Inference and Advanced Analyses

Use this reference after object, design, QC, and identity gates are adequate.
Define the estimand before selecting a method.

## Differential Expression

Distinguish:

- cluster markers: exploratory features distinguishing cell partitions;
- within-sample cell variation: descriptive or model-based cell-level effects;
- condition effects: replicated sample-level inference.

For condition effects, default to sample-by-cell-type pseudobulk counts with a
design and contrast matching pairing, repeated measures, batch, and relevant
covariates. Explore pseudobulk samples before modeling. Filter low-expression
genes per cell type, report effect sizes and uncertainty, and control the
declared multiple-testing family.

For each cell type, check actual independent donor counts, missing paired
specimens, low cell yield and low expression before defining the model. Do not
aggregate all patients together. For patient-level pre/post designs aggregate
by specimen and cell type, retain patient ID, and model the paired contrast;
do not collapse both time points into one patient pseudobulk. Check design rank
and the requested contrast under all covariates, not only batch/condition.
Use leave-one-donor-out diagnostics when a small number of donors may dominate.

Cell-level tests that ignore donor or sample are pseudoreplicated and cannot
support condition-level claims. Mixed models may be appropriate when their
sampling structure and assumptions are explicit.

## Differential Abundance and Composition

Cell proportions are compositional and sampling depth varies. Define whether
the target is:

- a labeled cell-type or state proportion;
- an absolute abundance with external denominator;
- a continuous neighborhood-level change.

Use sample-level compositional models for known labels. Use neighborhood
methods for continuous or transitional populations. Review sample size, zeros,
reference category, covariates, tissue sampling, and QC-induced depletion.
Report effect direction and credible or confidence intervals, not only
significance.

## Pathways and Programs

Separate:

- gene-set enrichment testing;
- per-cell or per-sample activity scoring;
- regulatory activity inference.

Verify gene identifiers, species, set version, directionality, overlap, and
gene coverage. For complex designs, prefer sample-level gene-set testing or
aggregate scores with a model matching the experimental unit. Avoid
double-dipping by testing a gene set selected from the same contrast without
acknowledging selection. Redundant gene sets are not independent discoveries.

## Pseudotime and Trajectories

Require a plausible biological process, approximate root or temporal
orientation, adequate state coverage, and a topology compatible with the
method. Compare inferred order with known markers, time points, perturbations,
or lineage information. Test root, feature, graph, and subset sensitivity.

Pseudotime orders observations along a model; it does not establish lineage,
elapsed time, or causality.

## RNA Velocity

Require spliced and unspliced counts and a process whose time scale is
compatible with RNA kinetics. Review phase portraits, gene fits, lineage
restriction, multiple kinetics, sampling density, and model assumptions.

Velocity arrows are local transcriptional direction estimates. They do not by
themselves prove fate, transition, or disease progression. Prefer independent
time-course or lineage-tracing support for directional claims.

Distinguish the assumptions of the selected model: dynamical models do not
simply share every steady-state-model assumption. Check donor-specific fits,
heterogeneous kinetics and missing intermediate states; an attractive vector
field cannot settle a disputed lineage topology.

## Gene Regulatory Networks

Expression-derived networks are hypotheses about regulatory association. Audit
feature filtering, transcription-factor priors, sample and cell coverage,
stability across resampling, and enrichment of known motifs or chromatin
evidence. Report regulator activity separately from direct physical binding or
causal regulation.

## Cell-Cell Communication

Ligand-receptor inference assumes transcript abundance is informative about
protein availability and interaction. Require adequate annotation, expression
prevalence, sample replication, and a defined sender-receiver question. Use
consensus or complementary methods when appropriate, test differential
signaling at the sample level, and connect ligands to receiver programs.

An inferred interaction is a ranked hypothesis, not proof of protein binding,
spatial contact, signaling flux, or functional consequence. Seek spatial,
protein, perturbation, or blocking evidence for stronger claims.

Record the interaction database/version, species mapping, complex subunits and
cofactors. Distinguish contact, secreted and ECM interactions; spatial proximity
is informative at a mechanism-appropriate scale. Review whether altered cell
numbers or detection rates produce the apparent difference. Differential tests
and null/label permutations must preserve donor and pairing structure rather
than treating every cell as an independently randomized sample.

## Claim Calibration

| Evidence | Defensible wording |
| --- | --- |
| Single object or visualization | observed, enriched, consistent with |
| Replicated sample-level association | associated with, differs between |
| Temporal ordering alone | preceded the measured response; alternatives remain |
| Controlled perturbation with target/viability controls | contributed to the phenotype in the tested system |
| Orthogonal functional validation | supports a mechanism |
| Independent clinical validation | supports translational relevance |

Always name plausible alternatives, sensitivity checks, and the next evidence
that would materially strengthen or falsify the interpretation.

These rows are wording examples, not an evidence hierarchy. Assess measurement,
identification, replication and transport separately: external clinical
association does not become causal merely by being clinical.
