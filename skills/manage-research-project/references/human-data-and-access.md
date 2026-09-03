# Human data and access controls

Use this reference for human, clinical, controlled-access or otherwise
sensitive data. It is a scientific and operational checklist, not legal advice
or an ethics approval.

## Minimum governance record

Create `docs/DATA_GOVERNANCE.md` only when applicable and record:

- data classification and access class;
- IRB/ethics, consent, DUA or repository approval references and scope;
- permitted and prohibited uses;
- approved storage/compute environment and authorized roles;
- redistribution, publication and derived-output review constraints;
- retention, deletion and incident-escalation requirements;
- responsible owner and next review date.

Record references and statuses, not approval documents containing identifiers.
Do not claim compliance merely because the template is filled.

## Identifier and leakage controls

- Never write names, direct identifiers, credentials, tokens or linkage keys to
  project docs, prompts, logs, manifests or version control.
- Keep coded subject IDs distinct from specimen, aliquot, library, image, cell
  and observation IDs; document the hierarchy without the re-identification
  table.
- Split training/validation/test data at the independent subject level whenever
  subjects contribute multiple observations.
- Do not report sample count as independent `n` when several samples belong to
  one patient or donor.
- Review small cells, rare combinations and free text for disclosure risk
  before sharing derived tables or figures.

## Files and archives

- Keep restricted raw data in the authorized location; project documents may
  point to an approved logical reference.
- Do not duplicate controlled raw data into snapshots, cloud folders or
  portable archives without explicit authorization.
- Redact sensitive command arguments and environment values from run logs.
- Confirm access before handing work to another person or agent; a restart
  prompt must never contain a credential.
- Follow the governing retention/deletion procedure rather than deleting data
  ad hoc.
