# Biomarker and Translation Reasoning

Use this module when a molecular or cellular feature is proposed to classify,
forecast, predict treatment benefit, monitor exposure, or guide a decision.

## Name the Biomarker Role

| Role | Question |
| --- | --- |
| Diagnostic | Does the marker distinguish a defined disease state? |
| Prognostic | Does it forecast outcome independent of a treatment choice? |
| Predictive | Does it identify differential benefit from one intervention versus another? |
| Pharmacodynamic | Does it change with target engagement or exposure? |
| Monitoring | Does longitudinal change track disease or response? |
| Mechanistic | Does it represent a causal process rather than only correlate with it? |

Distinguish a **predictive biomarker of treatment effect** from an **outcome
prediction model in a specified treatment setting**. One treatment arm can
support prediction of response in that setting with adequate validation; it
cannot by itself establish differential benefit versus another treatment.
For treatment-effect prediction, specify the comparator and biomarker-by-
treatment interaction or another justified effect-modification estimand.
An interaction on one effect scale need not imply interaction on another.

## Translation Ladder

1. analytical validity of the measurement;
2. discovery association in the correct experimental unit;
3. locked marker definition and threshold;
4. internal validation without leakage;
5. independent external validation;
6. calibration and subgroup robustness;
7. comparison with clinical baselines;
8. decision utility and prospective evaluation.

Strong biological plausibility does not replace predictive validation.

## Audit the Design

Check:

- intended-use population and clinical decision;
- outcome definition and assessment time;
- treatment assignment and comparator;
- sample timing relative to intervention;
- prevalence, spectrum, and site effects;
- missingness and censoring;
- feature selection leakage;
- patient/group separation throughout feature selection, preprocessing and
  nested model tuning; never place cells from one patient in train and test;
- threshold selection and locking;
- discrimination, calibration, uncertainty, and clinical utility.

Do not require a dichotomized threshold when intended use is a continuous risk
model. Lock the feature definition, preprocessing and model first; lock a
decision threshold only when the intended clinical action requires one.

## Single-Cell Translation

Determine whether the proposed marker is:

- a cell abundance;
- a cell state or program;
- a clone;
- an ecosystem or spatial pattern;
- a composite signature.

Specify how it will be measured reproducibly outside the discovery assay and
whether tissue sampling variability overwhelms the signal.

## Claim Boundaries

- Discovery association is not a validated biomarker.
- Prognostic association is not treatment prediction.
- Response association is not target engagement.
- Cross-validation is not independent external validation.
- Statistical improvement is not clinical utility.
- A cohort-derived threshold is not portable until locked and tested.

## Output

Return biomarker role, intended use, locked versus exploratory components,
validation stage, leakage and generalizability risks, required comparator, and
the smallest evidence needed for the next translational claim.
