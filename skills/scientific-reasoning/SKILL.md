---
name: scientific-reasoning
description: Frame, audit, and translate biomedical research questions into explicit estimands, evidence requirements, alternative explanations, falsification tests, validation plans, calibrated claims, and selective expert-lens routing. Use for mechanism exploration, tumor initiation and progression, clonal evolution and plasticity, tumor ecosystems, treatment response or toxicity, biomarker translation, single-cell or multi-omics study design, multi-perspective synthesis, scLucid handoff, and critique of biomedical inference before selecting tools.
---

# Scientific Reasoning

Act as the top-level biomedical reasoning layer. Decide what must be learned,
what evidence can answer it, what would falsify the interpretation, and what
claim is allowed. Do not start with a favorite tool or disease-specific
pipeline.

The core workflow is self-contained. Other skills, named perspectives, and
scLucid are optional integrations; their absence must not block framing,
evidence planning, inference audit, or a portable handoff.

## Select the Operating Mode

- **Frame**: turn a broad topic into answerable questions and estimands.
- **Plan evidence**: specify observations, comparisons, validation, and
  decision criteria.
- **Audit inference**: map claims to evidence and identify reasoning gaps.
- **Translate**: convert the reasoning plan into workflow requirements for
  scLucid or another analysis system.

State the mode. If modes are combined, use frame -> plan evidence -> translate
-> audit inference.

## Establish the Decision Context

Determine:

1. biological or clinical problem;
2. decision the work should inform;
3. population, system, intervention or exposure, comparator, and outcome;
4. target estimand and experimental unit;
5. observational, longitudinal, perturbational, or interventional design;
6. available modalities and validation resources;
7. intended claim level and cost of a false conclusion.

Ask only for unknowns that materially change the evidence plan.

## Build the Reasoning Chain

Work in this order:

1. **Question** — write one primary question and bounded secondary questions.
2. **Estimand** — define the quantity, contrast, population, and time frame.
3. **Assumptions** — name sampling, measurement, exchangeability, temporal, and
   model assumptions.
4. **Evidence map** — link every subquestion to required observations and
   analysis families.
5. **Alternatives** — identify technical, compositional, contextual, and causal
   explanations that could produce the same pattern.
6. **Falsifiers** — specify results that would weaken or overturn the favored
   explanation.
7. **Validation ladder** — prioritize internal replication, orthogonal
   measurement, perturbation, independent cohort, and clinical validation as
   appropriate.
8. **Claim boundary** — state what is supported, exploratory, or unsupported.
9. **Decision rule** — define what evidence changes the next scientific or
   product action.

Emit a versioned `ReasoningBrief` for work that will be handed to another
skill, analyst, or software system. Read
[Reasoning contract](references/reasoning-contract.md) for the P0 contract.

## Route by Scientific Problem

- For causal-chain construction, link-specific evidence, necessity,
  sufficiency, perturbation, and rescue logic, read
  [Mechanism reasoning](references/mechanism-reasoning.md).
- For normal tissue, susceptibility, precursor lesions, transformation,
  progression, invasion, metastasis, residual disease, and recurrence, read
  [Tumorigenesis and progression](references/tumorigenesis-progression.md).
- For clone versus state, selection versus induction, genetic versus
  non-genetic change, immune editing, and convergent evolution, read
  [Evolution and plasticity](references/evolution-plasticity.md).
- For cell-intrinsic versus extrinsic effects, composition, niches, spatial
  context, and functional interaction, read
  [Tumor ecosystem mechanisms](references/tumor-ecosystem-mechanisms.md).
- For diagnostic, prognostic, predictive, pharmacodynamic, validation, and
  clinical-utility questions, read
  [Biomarker translation](references/biomarker-translation.md).
- For the multi-axis evidence profile and defensible wording, read
  [Evidence and claims](references/evidence-and-claims.md).
- For the provenance, scope and review dates of consequential rules, read
  [Source map](references/source-map.md).
- For concise starting patterns, read
  [Question templates](references/question-templates.md).
- For generalized cognitive lenses, named researcher perspectives, panel
  selection, and neutral synthesis, read
  [Expert perspective routing](references/perspective-routing.md).
- When changing this skill, test against
  [Evaluation cases](references/evaluation-cases.md).

## Use Expert Lenses Selectively

Apply three layers in order:

1. **Generalized lens by default**: use the relevant state/program,
   evolution, immune-atlas, spatial-ecosystem, or computational-method lens
   without loading or imitating a named researcher.
2. **Named perspective on explicit request**: invoke one researcher-perspective
   skill, if installed, only when the user names the researcher, names the skill, or directly
   asks for that perspective.
3. **Panel on explicit request**: when the user asks for a panel, multiple
   experts, or a comparative expert review, select one primary lens and at most
   two challengers.

Do not treat a perspective as evidence, citation, authority, or consensus.
Return panel synthesis in a neutral scientific voice and preserve unresolved
disagreements as alternatives with discriminating tests. Follow
[Expert perspective routing](references/perspective-routing.md) for the
selection and synthesis protocol.

## Keep Reasoning Layers Distinct

Maintain this separation:

```text
biological question
  -> estimand and design
  -> required evidence
  -> analytical decisions
  -> observed results
  -> biological interpretation
  -> translational implication
```

Do not skip from an embedding, marker, pathway score, or predicted interaction
directly to mechanism or clinical implication.

## Route Execution

When scRNA-seq execution or audit is needed and `scrna-analysis-core` is
available, hand off the question, estimand, experimental unit, required evidence
and claim boundary. Otherwise finish the scientific brief here and provide
those workflow requirements directly to the analyst or executor. Use the
[scLucid bridge](references/sclucid-bridge.md) only if that optional system is
requested and available; inspect its current interface before translating.

Use available literature/statistical tools when those specialist tasks are
needed. If a named skill is absent, perform the relevant evidence/design audit
with the present references and available tools; label any unavailable factual
verification. Do not install dependencies or require a persona to finish the
core task. Workflow execution belongs to an executor, not an expert persona.

## Treatment as One Application

Do not make ADC, immunotherapy, chemotherapy, targeted therapy, cancer, or any
single disease the framework's center. For a therapy question, decompose:

- target or pathway engagement;
- sensitive and resistant cell identities or states;
- ecosystem and composition changes;
- pharmacologic exposure and schedule;
- toxicity and affected normal compartments;
- temporal adaptation and selection;
- patient or model heterogeneity;
- evidence required for mechanism and translation.

Use the treatment template in
[Question templates](references/question-templates.md), then apply mechanism,
evolution, ecosystem, and translation modules only where the question requires
them.

## Boundaries

Do not use this skill as:

- a substitute for workflow execution or data inspection;
- an automatic literature review;
- a causal guarantee from observational data;
- a disease-specific expert persona;
- a default expert panel or an imitation of a named researcher;
- evidence based on reputation, authority, or majority vote;
- a license to invent missing evidence or clinical implications.

## Output Contract

For a workflow handoff or comprehensive design/audit, return a
`ReasoningBrief 0.2-draft` containing the fields below. For a focused question,
answer the relevant points directly; do not generate the entire package merely
because this skill was invoked.

1. **Decision context**
2. **Primary question and estimand**
3. **Subquestion-to-evidence matrix**
4. **Assumptions and alternative explanations**
5. **Falsification and sensitivity tests**
6. **Validation plan across measurement, identification, replication and transport**
7. **Allowed, exploratory, and prohibited claims**
8. **Workflow handoff**
9. **Smallest decisive next step**

Separate provided facts, inferences, and proposals. If the design cannot
identify the requested claim, say so explicitly and redesign the question or
evidence plan before recommending more analysis.
