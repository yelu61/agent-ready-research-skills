# Expert Perspective Routing

Use this P2 protocol to add expert cognitive diversity without turning
`scientific-reasoning` into a collection of personas. The output remains one
evidence-calibrated `ReasoningBrief 0.2-draft`.

## Contents

- Invariants
- Three routing layers
- Generalized cognitive lenses
- Named perspective mapping
- Panel selection and synthesis
- Contract integration
- When not to route

## Invariants

1. Start from the scientific question, estimand, design, and unresolved
   inference risk.
2. Use the smallest number of lenses that materially changes the evidence
   plan.
3. Treat every lens as a source of questions and failure modes, never as
   evidence or citation.
4. Keep facts, inferences, and proposals separate.
5. Preserve one shared `ReasoningBrief`; do not create competing briefs that
   silently redefine the question.
6. Do not infer a user's desire for role-play from the scientific topic alone.

## Three Routing Layers

### Layer 1: Generalized Lens

Use a generalized lens by default. Apply its questions directly without
loading, naming, or imitating a researcher-perspective skill.

### Layer 2: Named Perspective

Load one named perspective only when the user:

- names the researcher;
- names the skill; or
- explicitly asks for that person's perspective.

For a single named perspective, follow that skill's own activation, safety,
research, and output rules. `scientific-reasoning` still owns the estimand,
evidence requirements, falsifiers, and claim boundary.

Named perspectives are optional installed extensions, never bundled runtime
dependencies. If absent, state that limitation and use the corresponding
generalized lens below; do not impersonate that researcher or attribute the
result to them. Continue the full core reasoning task without installation.

### Layer 3: Panel

Use panel mode only when the user explicitly requests a panel, multiple expert
perspectives, debate, or comparative review. Select one primary lens and no
more than two challengers. Do not activate all available perspectives.

## Generalized Cognitive Lenses

| Lens | Use when the unresolved problem is | Questions contributed | Typical blind spot |
| --- | --- | --- | --- |
| State, program, and plasticity | discrete clusters versus continuous programs; genetic versus non-genetic state; hierarchy versus transition | Are states continuous? Are programs recurrent? Can clone, lineage, and context be separated? What would demonstrate transition? | may underweight clinical sampling, clonal architecture, or deployment |
| Evolution, clonality, and selection | trunk versus branch; selection versus induction; immune editing; recurrence or metastasis | What is clonal? What sampling supports the phylogeny? Which pressure selects the phenotype? Is the trajectory longitudinally constrained? | may overextend genomic evolution when state plasticity or ecology dominates |
| Immune atlas, cohort, and translation | immune-state taxonomy; cross-cohort recurrence; pan-cancer versus disease-specific patterns; clinical pairing | Is the landscape sufficiently mapped? Is the state reproducible across patients? What is shared versus context-specific? Is the cohort linked to a decision? | atlas breadth can outpace mechanism or spatial resolution |
| Spatial ecosystem, precursor, and validation | niches, multicellular organization, normal-to-precursor-to-tumor change, multimodal validation | Where is the state located? Which neighbors and stages matter? Is the finding supported by computational, experimental, and clinical evidence? | spatial association can be mistaken for interaction or causality |
| Computational model, benchmark, and uncertainty | integration, latent representations, trajectories, prediction, method choice, model reliability | What is the data-generating assumption? Which baseline and metrics test the claim? Is biological signal preserved? Is uncertainty calibrated? | technical performance can become detached from the biological estimand |

These lenses are durable abstractions. Update them only when a recurring
reasoning operation changes, not when a named skill adds biographical detail,
new terminology, or stylistic preferences.

## Named Perspective Mapping

| Explicit request or panel need | Optional skill | Distinctive contribution | Guardrail |
| --- | --- | --- | --- |
| Tirosh; meta-programs; continuous tumor states; program scoring | `tirosh-perspective` | program-level heterogeneity, genetic versus non-genetic decoupling, plasticity, recurring programs | do not let a program score establish lineage, transition, or mechanism |
| Swanton; TRACERx; branched evolution; immune editing; MRD | `swanton-perspective` | multi-region and longitudinal sampling, clonality, selection, evolutionary constraint, prospective validation | do not infer clone structure or evolutionary direction from scRNA alone |
| Zhang or BIOPIC; pan-cancer immune atlas; cohort strategy | `zhang-zemin-perspective` | states-over-types, cross-patient recurrence, atlas-to-mechanism staging, tool-cohort-clinical linkage | do not equate atlas completeness or recurrence with causal validation |
| Linghua Wang; spatial niche; ecotype; precursor lesion | `linghua-wang-perspective` | spatial context, disease-stage continuum, multimodal and wet-dry-clinical validation | do not equate proximity, ecotype, or signature transfer with function |
| Theis; scVI/scIB/moscot; benchmark; uncertainty; foundation model | `theis-perspective` | probabilistic assumptions, benchmarking, uncertainty, integration and generative-model scrutiny | do not optimize a method metric while losing the biological estimand |

Topic overlap alone is not permission to invoke a named perspective. In the
default path, use the generalized lens in the preceding table.

Respect the installed extension's activation policy. This skill only invokes
named extensions on an explicit request and never edits their metadata or
assumes they are present. Panel orchestration may use generalized lenses alone.

## Panel Selection and Synthesis

### Select

1. Identify the single uncertainty most likely to invalidate the primary
   claim; assign its lens as **primary**.
2. Choose a first challenger for the strongest biological alternative.
3. Choose a second challenger only if it adds a distinct design, spatial,
   evolutionary, translational, or computational failure mode.
4. Stop at three lenses. If more are plausible, list the deferred lens and why
   it is lower priority.

Example: for a treatment-associated tumor state, use state/program as primary,
evolution/selection to challenge induction, and spatial ecosystem to challenge
cell-intrinsic interpretation.

### Give Every Lens the Same Input

Provide the current `ReasoningBrief`, available evidence, and known missing
data. Ask each lens for the same compact memo:

```yaml
lens: null
role: primary
question_reframe: null
candidate_hypotheses: []
critical_assumptions: []
alternative_explanations: []
discriminating_evidence: []
falsifiers: []
validation_priorities: []
smallest_decisive_next_step: null
```

This memo is an internal synthesis aid, not a new public contract and not
`RunEvidence`.

### Synthesize

1. Record common ground only when the lenses rely on compatible assumptions.
2. Record disagreements as explicit competing hypotheses or assumptions.
3. Resolve a disagreement only with discriminating evidence, not reputation,
   rhetorical confidence, or majority vote.
4. Merge accepted contributions into one `ReasoningBrief`:
   - hypotheses into `mechanism_hypotheses`;
   - competing accounts into `alternative_explanations`;
   - vulnerabilities into `assumptions`;
   - decisive failures into `falsifiers`;
   - required observations into `required_evidence`;
   - follow-up work into `validation_ladder`.
5. Preserve existing IDs. Assign new `H*` and `E*` IDs rather than
   renumbering upstream items.
6. Return the final synthesis in a neutral scientific voice. If the user asked
   for a debate transcript, provide it separately from the contract.

## Contract Integration

P2 does not change `ReasoningBrief 0.2-draft`. Lens selection is process
metadata, not scientific evidence. Do not add a person name to
`required_evidence`, `supports`, or `claim_boundary.supported`.

If provenance is useful, record a short human-readable note outside the
contract, for example: "P2 synthesis used state/program as primary and
evolution as challenger." The defensible output must remain understandable
without knowing any researcher identity.

## When Not to Route

- For QC, normalization, integration parameters, clustering resolution, or
  executable scRNA workflow review, use `scrna-analysis-core`.
- For current factual claims, publications, citations, or database knowledge,
  use literature-search or biomedical-knowledge tools.
- For contrasts, covariates, pseudobulk, repeated measures, effect sizes, or
  multiplicity, use a statistical-review skill.
- For a narrow factual or syntax question, answer directly.
- For scLucid execution, pass the stabilized `ReasoningBrief`; do not make
  scLucid depend on any named perspective skill.
