# Scientific Reasoning Evaluation Cases

Use these cases to test problem routing, evidence calibration, P0 handoff,
coverage beyond treatment, and P2 expert-lens selection.

These are authored evaluation designs, not records of completed model tests.
For an independent evaluation, give the agent only the skill, user prompt and
input material. Keep reviewer criteria separate until the output is saved.
Record model/version, date, available tools/extensions, output, observed actions
and criterion-level reviewer judgments. A structural JSON pass is not a pass
on scientific reasoning. Include feasible tasks so excessive blocking fails too.

## 1. Broad Mechanism

Prompt: “Find the resistance mechanism from this single-cell dataset.”

Expected: define phenotype and comparator; build a link-specific causal chain;
retain alternatives; require perturbational validation; avoid claiming
mechanism from association.

## 2. ADC Toxicity

Prompt: “Which cells cause ADC corneal toxicity?”

Expected: distinguish target, payload, bystander, immune, and injury responses;
define exposure and normal-tissue model; identify temporal and functional
evidence.

## 3. Cell of Origin

Prompt: “This cluster is the cell of origin of the tumor.”

Expected: distinguish lineage from state of origin; request normal/precursor,
lineage, genomic, or perturbational evidence; reject annotation alone.

## 4. Cancer Progression

Prompt: “This cross-sectional trajectory reconstructs tumor progression.”

Expected: reject false chronology; separate stage association from temporal
order; request longitudinal, lineage, genomic, or precursor evidence.

## 5. Metastasis

Prompt: “The EMT-high population drives metastasis.”

Expected: separate EMT-like state, invasion, dissemination, and colonization;
require paired or lineage-linked and functional evidence.

## 6. Evolution Versus Plasticity

Prompt: “The treatment-induced state proves acquired evolution.”

Expected: compare selection, induction, reversible adaptation, new mutation,
ecosystem, and sampling models; specify discriminating evidence.

## 7. Immune Editing

Prompt: “Loss of T cells shows immune editing.”

Expected: distinguish abundance, exclusion, dysfunction, antigen visibility,
and clone selection; require genomic, temporal, or functional evidence.

## 8. Tumor Ecosystem Communication

Prompt: “Ligand-receptor analysis proves stromal protection.”

Expected: separate composition, state, association, proximity, and function;
request receiver, protein, spatial, blocking, or rescue evidence.

## 9. Predictive Biomarker

Prompt: “This signature predicts patient response.”

Expected: distinguish prognostic from predictive use; require treatment
comparator, locked model, leakage control, calibration, and external validation.

## 10. Pharmacodynamic Biomarker

Prompt: “A post-treatment pathway score proves target engagement.”

Expected: examine timing, specificity, dose response, direct target readout, and
alternative stress responses; calibrate the claim.

## 11. Developmental Trajectory

Prompt: “Velocity arrows prove one mature cell type becomes another.”

Expected: audit kinetic, root, topology, and steady-state assumptions; request
time, lineage, or perturbation support.

## 12. scLucid Handoff

Prompt includes a paired multi-sample design and a defined disease-mechanism
question.

Expected: emit stable question and evidence IDs in a `ReasoningBrief`; map
metadata to `ProjectContext`; route scRNA execution to
`scrna-analysis-core`; do not claim P0 draft objects already exist as APIs.

## 13. Generalized Lens Without Persona

Prompt: “Should these tumor clusters be treated as fixed cell types or
continuous states?”

Expected: use the generalized state/program/plasticity lens; define
discriminating evidence; do not automatically invoke, name, or imitate Tirosh.

## 14. Explicit Named Perspective Routing

Prompt set: “Use Tirosh to review our meta-programs”; “Use Swanton to challenge
our recurrence model”; “Use Zhang's perspective on this immune atlas”; “Use
Linghua Wang's perspective on this spatial precursor study”; “Use Theis to
audit this integration benchmark.”

Expected: route each prompt to only the named skill; retain the shared
scientific question and claim boundary; treat the perspective as a critique
lens rather than evidence. Respect the installed extension's activation policy;
if missing, disclose that fact and use the matching generalized lens without
impersonation or requiring installation.

## 15. Primary and Challenger Selection

Prompt: “Use an expert panel to evaluate whether therapy induced a resistant
tumor state.”

Expected: choose state/program as primary, evolution/selection as a challenger,
and add a third lens only if it contributes a distinct failure mode; use at
most three lenses.

## 16. Panel Disagreement

Prompt: “One expert says selection, another says plasticity, and another says
the niche explains the change. Give the panel's answer.”

Expected: do not vote; represent three competing explanations, assumptions,
falsifiers, and discriminating evidence; preserve unresolved disagreement.

## 17. No Expert Route for Workflow Parameters

Prompt: “Which QC thresholds and integration settings should I use?”

Expected: route to `scrna-analysis-core`; do not select a researcher based on
topic overlap; request the dataset setup and evidence target.

## 18. Neutral Contract After Panel

Prompt: “Turn the panel review into a scLucid-ready plan.”

Expected: emit one neutral `ReasoningBrief 0.2-draft`; preserve existing IDs;
add new hypotheses and evidence IDs without renumbering; do not serialize
researcher names as evidence or make scLucid depend on perspective skills.

## Material-backed case A: One-arm outcome model

User prompt: “This signature predicts ADC benefit; can we use it to select the
treatment?” Input material: synthetic 30-patient single-arm cohort; pretreatment
scRNA-seq; response measured at week 12; every patient's cells were randomly
split across train/test; features were selected on the entire cohort; reported
test AUC 0.94; no alternative-treatment cohort; no locked model or threshold.

Reviewer criteria: distinguish response prediction in this treatment setting
from differential treatment benefit; identify patient and feature-selection
leakage; propose donor-separated nested validation and model locking; specify
the comparator/effect-modification evidence needed for treatment selection.
Do not forbid all outcome modeling simply because there is one treatment arm;
do not accept the reported AUC as an independently validated performance claim.

## Material-backed case B: Stable resistance without a new mutation

User prompt: “The post-treatment state stayed high after washout, so it proves
genetic acquired resistance.” Input material: synthetic cell-line experiment;
baseline state rare by scRNA; enriched after drug; persists for 14 days after
withdrawal; no lineage barcode, no paired DNA, no pre-existing-clone sensitivity
assessment; state regulator expression shifts; growth rates differ.

Reviewer criteria: retain pre-existing clone/state selection, induced stable
non-genetic memory and new genetic change; separate clone from state and
timescale-limited non-reversion from genetic proof; specify lineage/genomic
and regulator perturbation evidence that could distinguish accounts. No single
preferred mechanism without new evidence, and no claim that every state must
rapidly reverse.

## Material-backed case C: Evidence axes and absent extensions

User prompt: “Rank the evidence and give us the next decisive experiment.”
Input material: synthetic independent human cohort association in 300 patients;
no intervention assignment or known-confounder table; separate organoid study
has randomized target knockout, viability controls and dosage-matched rescue
in three independent donors; no in vivo efficacy; scLucid and all named
perspective skills are unavailable.

Reviewer criteria: compare measurement, identification, replication and transport
separately; clinical association does not automatically outrank controlled
causal evidence; organoid evidence does not establish patient benefit; propose
a discriminating next experiment and complete the core brief without requesting
installation or attributing it to a missing expert. Acknowledge missing study
details instead of inventing them. This can be evaluated in prose; exact wording
or an ordinal score is not a grading requirement.
