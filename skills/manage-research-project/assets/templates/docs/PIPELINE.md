# Pipeline

Last updated: {{DATE}}

Document the workflows that actually exist. Keep authored code under
workflows/<workflow_id>/; keep implementation, execution and validation in
separate columns. A completed process is not automatically validated or
scientifically ready.

## Workflow map

    TODO: input
      -> workflows/<workflow_id>/scripts/<entrypoint>
      -> analysis/runs/<workflow_id>__<run_label>/
      -> results/ (question or domain-module navigation)

## Stage registry

| Stage ID | Analysis ID | Workflow ID | Entry point | Input artifact IDs | Config/spec | Output artifact IDs | Implementation status | Execution status | Technical validation status | Validation kind | Validation scope | Validation criterion | Validation evidence IDs | Latest run ID | Readiness scope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO | planned | not_run | not_assessed | TODO | TODO | TODO | TODO | TODO | TODO |

## Dependency and restart boundaries

| Stage ID | Depends on | Backend lock | Restartable checkpoint | Integrity check | Scientific/technical validation scope |
|---|---|---|---|---|---|
| TODO | TODO | workflows/TODO/backend.lock.json | TODO | TODO | TODO |

## Known gaps

- TODO: Missing code, failed execution, hidden state, unverified dependency,
  currency_status=stale or unsupported claim.

## Minimal reproduction commands

    # TODO: verify workflows/<workflow_id>/backend.lock.json
    # TODO: run workflows/<workflow_id>/scripts/<entrypoint>
