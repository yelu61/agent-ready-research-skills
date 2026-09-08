# Biomedical Question Templates

Select only the relevant template and adapt it to the project.

## Cell Identity and State

Primary question:

> Which replicated cell identities or states differ across the defined
> biological contexts, and are those differences compositional, intrinsic, or
> technical?

Evidence:

- identity and state definitions with uncertainty;
- sample-level prevalence and expression;
- technical and composition sensitivity;
- orthogonal markers or reference mapping;
- independent or held-out validation.

## Treatment Response and Resistance

Decompose the primary question:

1. Is the molecular target or pathway present and engaged?
2. Which tumor or normal cell states are intrinsically sensitive?
3. Which pre-existing or induced states associate with resistance?
4. Does treatment change abundance, state, or both?
5. Does the ecosystem protect, potentiate, or redistribute response?
6. Are findings shared across patients or driven by a subset?
7. Which observation distinguishes adaptation from selection?
8. What perturbation would test the leading mechanism?

Therapy-specific additions:

- chemotherapy: damage response, proliferation, lineage vulnerability, repair;
- targeted therapy: dependency, pathway inhibition, bypass signaling;
- ADC: target density and heterogeneity, payload response, internalization,
  bystander effects, normal-tissue target or payload sensitivity;
- immunotherapy: antigen presentation, effector state, exclusion, suppressive
  ecosystems, clonality, prior treatment.

Do not let therapy class replace the actual estimand.

## Toxicity

Ask:

- which normal compartment is exposed and vulnerable;
- whether toxicity is target-dependent, payload-dependent, immune-mediated, or
  secondary to tissue injury;
- whether the observed state precedes injury or follows it;
- how dose, schedule, and recovery affect the state;
- which normal model best matches clinical tissue and exposure.

## Development and Trajectory

Ask:

- what start, intermediate, and terminal states are biologically plausible;
- whether sampling covers the process;
- whether order is known from time, lineage, or perturbation;
- which alternative topology fits the same snapshot;
- what lineage or temporal evidence validates direction.

## Tumor Ecosystem

Separate:

- malignant identity and genomic structure;
- malignant transcriptional programs and plasticity;
- immune and stromal identities and states;
- spatial or ecological co-occurrence;
- patient-level recurrence;
- treatment or outcome association;
- functional interaction evidence.

Avoid turning correlation between compartments into communication or mechanism
without additional evidence.

## Method Development

Define:

- target task and decision;
- benchmark datasets and ground truth;
- baselines and ablations;
- biological conservation and technical correction metrics;
- failure cases, calibration, compute, and reproducibility;
- whether metric improvement changes a biological conclusion.
