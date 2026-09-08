# Mechanism Reasoning

Use this module to determine whether observations merely fit a mechanism or
actually support one.

## Build the Causal Chain

Represent the proposed mechanism as explicit links:

```text
cause or perturbation
  -> initial molecular event
  -> signaling or regulatory change
  -> cell state and function
  -> population or ecosystem change
  -> tissue phenotype
  -> disease or clinical consequence
```

Do not let evidence for one link stand in for the entire chain.

## Audit Every Link

For each arrow ask:

- Does the cause precede the effect?
- Does changing the cause change the effect?
- Is there a dose, duration, or exposure-response relationship?
- Is the effect specific enough to distinguish alternatives?
- Is the mediator measured directly or inferred from a proxy?
- Does inhibition, depletion, or knockout weaken the effect?
- Does rescue restore the effect?
- Does orthogonal measurement support the same link?
- Is the result replicated in the correct experimental unit?

For consequential causal claims, sketch the relevant causal graph and identify
pre-exposure confounders separately from mediators and selection/collider
variables. Do not adjust for every available covariate. Align exposure, sample
timing and outcome time zero; ask how enrollment, survival and missing tissue
select the observed population. A perturbation can have off-target or general
toxicity effects: use orthogonal perturbations, target engagement and viability
controls. Rescue needs an appropriate expression/dose range and control vector;
overexpression rescue alone may bypass the proposed mediator.

## Classify Mechanistic Evidence

| Evidence | Interpretation |
| --- | --- |
| Co-expression, enrichment, or correlation | compatible with a mechanism |
| Replicated temporal ordering | supports direction |
| Perturbation with controls | supports causal contribution in that system |
| Loss-of-function plus rescue | supports mediator necessity and specificity |
| Gain-of-function alone | tests sufficiency, not normal necessity |
| Orthogonal functional confirmation | strengthens the proposed mechanism |
| Independent human validation | extends relevance, not necessarily causality |

Avoid saying “proved” when only one link has been tested.

## Use Competing Mechanisms

For each favored mechanism, retain at least one plausible alternative. State:

1. observations explained by both;
2. observations unique to each;
3. the smallest experiment or dataset that separates them;
4. results that would falsify the favored mechanism.

## Single-Cell Boundary

Single-cell transcriptomics can localize candidate cells, states, programs, and
associations. It usually does not directly establish:

- protein activity or localization;
- biochemical binding;
- signaling flux;
- lineage ancestry;
- necessity or sufficiency;
- tissue-level functional consequence.

Use protein, spatial, genomic, temporal, perturbational, lineage, or functional
evidence according to the missing causal link.

## Output

Return the causal chain, evidence per link, competing mechanisms, falsifiers,
current mechanism strength, and smallest discriminating validation.
