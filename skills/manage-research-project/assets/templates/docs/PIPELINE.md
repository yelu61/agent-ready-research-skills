# Pipeline

Last updated: {{DATE}}

Document the workflows that actually exist. {{SOURCE_POLICY}}
Keep implementation, execution and validation in
separate columns. A completed process is not automatically validated or
scientifically ready.

## Workflow map

    TODO: input
      -> {{ENTRY_POINT}}
      -> {{RUN_ROOT}} (preserved native run bundle)
      -> {{RESULTS_ROOT}} (question or domain-module navigation)

## Stage registry

| Stage ID | Analysis ID | Workflow ID | Entry point | Input artifact IDs | Config/spec | Output artifact IDs | Implementation status | Execution status | Technical validation status | Validation kind | Validation scope | Validation criterion | Validation evidence IDs | Latest run ID | Readiness scope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO | planned | not_run | not_assessed | TODO | TODO | TODO | TODO | TODO | TODO |

## Dependency and restart boundaries

| Stage ID | Depends on | Backend lock | Restartable checkpoint | Integrity check | Scientific/technical validation scope |
|---|---|---|---|---|---|
| TODO | TODO | {{BACKEND_LOCK}} | TODO | TODO | TODO |

## Known gaps

- TODO: Missing code, failed execution, hidden state, unverified dependency,
  currency_status=stale or unsupported claim.

## Minimal reproduction commands

    # Verify the actual backend lock: {{BACKEND_LOCK}}
    # Record the actual reproduction command for: {{ENTRY_POINT}}
