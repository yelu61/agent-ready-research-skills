---
name: critical-paper-reading
description: "Critically read, review, or assess a scientific paper beyond summary. Use for claim–evidence mapping, causal calibration, novelty and assumption checks, statistical and reproducibility critique, reviewer-style assessment, journal clubs, or actionable follow-up design from a paper, preprint, PDF, DOI, or link."
---

# Critical Paper Reading

Evaluate what a paper actually establishes, how strongly the evidence supports
its claims, where the conclusions may fail, and what useful work should follow.
Treat author statements, displayed results, your inference, and external context
as distinct evidence classes.

## Core rules

1. Establish source completeness before judging the work.
2. Map central claims to specific evidence instead of retelling the paper.
3. Match causal language to the experimental design.
4. Separate statistical significance from effect size, robustness, and practical
   importance.
5. Distinguish genuine novelty from a new dataset, implementation, scale, or
   presentation of an existing idea.
6. Prioritize decisive weaknesses and feasible remedies over exhaustive fault
   lists.
7. Never invent missing controls, methods, statistics, figures, or supplementary
   results.

## Step 1: Establish the reading contract

Identify the available material and requested mode.

### Source-completeness gate

Record which sources are actually available:

- full text or PDF;
- figures and tables;
- methods;
- supplementary methods, figures, and data;
- code or data repository;
- abstract, DOI, or link only.

If the user provides only a DOI or link, retrieve and inspect the paper and any
necessary supplementary material when tools and access permit. If access fails,
say exactly what was unavailable. Do not reconstruct the study from memory or
judge reliability from the abstract alone.

Ask for additional material only when the missing source or user goal would
materially change the analysis. Otherwise proceed with a scoped assessment and
label the limitation.

Record the article identifier, preprint/published version, retrieval date and
available corrections or retractions. A failed status lookup is `not checked`,
not evidence that no correction exists. Read [methodology and sources](references/methodology.md)
for design-specific checks. Other skills are optional: use available tools
directly, or assess supplied material with explicit coverage limits. No other
skill or scLucid installation is required.

### Select a mode

Use the requested mode, or infer the narrowest one that satisfies the request:

- **Full critical read**: comprehensive scientific assessment.
- **Fast read**: concise orientation, strongest evidence, major caveats, and
  bottom line.
- **Reviewer**: strict but fair referee report with prioritized concerns and
  remedies.
- **Journal club**: discussion-ready structure and questions.
- **Project extension**: emphasis on opportunities, experiments, and analysis
  plans that build on the study.

State the selected mode briefly. Do not force every output section into short or
focused requests.

## Step 2: Orient to the study

In a short opening, identify:

- the real problem and why it matters;
- the study's central claim;
- the design, system, cohort, or benchmark used;
- the claimed advance over prior work;
- the highest-level conclusion that appears justified.

Avoid a section-by-section paper summary unless the user requests one.

## Step 3: Build the claim–evidence map

List only the central claims needed to support the paper's conclusion. For each,
record:

| Field | What to determine |
|---|---|
| Claim | The authors' substantive assertion |
| Evidence | The experiment, figure, analysis, or comparison supporting it |
| Evidence origin | Reported, inspected, inferred, external, or unavailable |
| Test relation | Direct, indirect, or not assessed for this exact claim |
| Evidence dimensions | Measurement, identification, mechanism, replication, external validity |
| Main caveat | The most consequential alternative explanation or missing control |
| Verdict | Supported, partially supported, overclaimed, contradicted, or not assessable |

Use these evidence-origin labels consistently, separately from the verdict:

- **Reported**: the authors state it, but it has not yet been independently
  evaluated in this reading.
- **Inspected**: the relevant result and available method were read. A direct
  test addresses the exact claim and can support or contradict it; an indirect
  test leaves additional explanations. Directness is not a positive verdict.
- **Inferred**: your interpretation rather than an explicit paper result.
- **External**: supported or challenged by information outside
  the paper.
- **Unavailable**: the necessary evidence is missing or inaccessible.

When citing evidence, point to the relevant figure, table, method, or supplement
when available.

## Step 4: Calibrate causal strength

Do not equate correlation, prediction, spatial proximity, enrichment, or
perturbation response with mechanism.

Assess distinct dimensions for each claim; there is no universal evidence rank:

| Dimension | Required reasoning |
|---|---|
| Measurement and estimation | What was measured, with what experimental unit, effect and uncertainty? |
| Causal identification | What estimand and design identify the effect, under which consistency, exchangeability, positivity and timing assumptions? |
| Mechanism | Which links have specific perturbation, necessity/sufficiency, mediator or rescue evidence in the tested system? |
| Replication | Are these new independent units, repeated measurements, reanalysis, or orthogonal assays on the same material? |
| External validity | Which populations, settings and outcomes were independently evaluated? |

External or prospective validation of association/prediction does not alone
establish causality or mechanism. Temporal ordering and dose response are not
sufficient identification conditions. Assess observational causal analyses
under their explicit assumptions; lack of randomization alone is not a
rejection rule. A specific intervention may support a local causal contribution
without establishing patient benefit. A perturbation can still be confounded by
off-target effects, toxicity, compensatory responses, or altered cell
composition. Mechanistic claims generally need orthogonal evidence and a
plausible chain between cause and phenotype.

## Step 5: Audit validity and reproducibility

Focus on checks that could change the conclusion.

### Design and statistics

- What is the biological unit of analysis?
- Are replicates biological, technical, paired, nested, or repeated measures?
- Is there pseudoreplication or an inflated effective sample size?
- Are allocation, exclusion, randomization, and blinding appropriate?
- Are batch, center, donor, ancestry, treatment, or other confounders addressed?
- Are effect sizes and uncertainty shown, not only P values?
- Is multiple testing handled where required?
- Are model assumptions, sensitivity analyses, and missing-data choices examined?
- What prespecified sample-size rationale, detectable effect or interval
  precision supports the principal claim? Do not substitute post-hoc observed
  power for uncertainty.

### Computation and reproducibility

- Are data splits performed at the correct independence level?
- Could feature selection, preprocessing, normalization, or tuning leak
  information across splits?
- Are baselines current, fairly tuned, and given comparable inputs and compute?
- Do ablations isolate the claimed contribution?
- Are code, versions, seeds, parameters, data provenance, and hardware reported?
- Is there validation on independent, shifted, prospective, or out-of-distribution
  data where the claim requires it?

### Evidence triangulation

Look for consistency across:

- independent cohorts or model systems;
- orthogonal assays;
- alternative analysis choices;
- positive and negative controls;
- perturbation and rescue;
- internal and external validation.

Absence of triangulation is not automatically fatal, but it limits the scope of
the conclusion.

## Step 6: Apply the relevant domain lens

Use only the lenses relevant to the paper.

| Domain | Priority checks |
|---|---|
| Single-cell or spatial omics | donor-level replication; batch and composition; annotation circularity; ambient RNA/doublets; spatial autocorrelation; integration artifacts; pseudobulk or hierarchical inference; orthogonal validation |
| Computational method or ML | leakage; split unit; baseline and tuning fairness; ablations; calibration; uncertainty; robustness; generalization; compute cost; reproducibility |
| Clinical or translational | cohort definition; endpoint validity; confounding; missingness; calibration; decision value; external and prospective validation; clinical feasibility |
| Wet-lab mechanism | reagent specificity; perturbation strength; off-target effects; dose and timing; rescue; necessity and sufficiency; model relevance; biological replication |
| Multi-omics | matched units; layer-specific QC; integration assumptions; feature-selection circularity; concordance versus causality; validation of cross-layer links |

## Step 7: Judge novelty and importance

For a current novelty or baseline claim, search the relevant literature and
record the search date, scope and closest comparators. If search is unavailable,
label novelty as provisional from supplied material.

Separate four questions:

1. Is the scientific question important?
2. Is the conceptual or technical advance genuinely new?
3. Is the evidence strong enough for the claimed advance?
4. Would the result change understanding, practice, or future experiments?

Classify novelty when useful:

- conceptual;
- methodological;
- empirical;
- scale or resource;
- translational;
- integrative.

State whether the apparent contribution is primarily a new principle, stronger
evidence, broader coverage, a useful tool, or a compelling application.

## Step 8: Identify failure modes and decisive next steps

Rank limitations by consequence:

- **Conclusion-threatening**: could reverse or invalidate the central claim.
- **Scope-limiting**: narrows where or to whom the conclusion applies.
- **Interpretation-limiting**: weakens mechanism or causal language.
- **Reporting or reproducibility**: prevents verification or reuse.

For each major issue, name:

1. the concern;
2. why it matters;
3. the result that would distinguish competing explanations;
4. a feasible remedy, analysis, or experiment.

For project-extension mode, prioritize follow-ups by:

- decisiveness;
- feasibility;
- expected information gain;
- dependence on unavailable resources;
- risk of merely repeating the paper.

## Output contract

Adapt length to the request. A full assessment should usually contain:

1. **Orientation and bottom line**
2. **Claim–evidence matrix**
3. **Strongest evidence**
4. **Weakest or overextended claims**
5. **Novelty and importance**
6. **Assumptions, validity, and reproducibility**
7. **Prioritized reviewer concerns**
8. **Actionable follow-up plan**
9. **Confidence and source limitations**

For reviewer mode, organize concerns as:

- brief summary and overall assessment;
- major concerns, ranked by impact;
- minor concerns;
- requested analyses or experiments;
- calibrated recommendation or decision tendency when requested.

Keep tone precise and fair. Credit what the study establishes before challenging
what it does not. Use calibrated phrases such as “supports,” “is consistent
with,” “suggests,” and “does not distinguish,” rather than rhetorical certainty.

## Final quality check

Before answering, verify:

- paper-internal evidence is separated from external context;
- central claims are tied to specific evidence;
- causal language matches design strength;
- missing information is marked rather than inferred;
- statistical and biological units are not conflated;
- major concerns are prioritized and actionable;
- the bottom line states what is established, what remains uncertain, and what
  would most change confidence.
