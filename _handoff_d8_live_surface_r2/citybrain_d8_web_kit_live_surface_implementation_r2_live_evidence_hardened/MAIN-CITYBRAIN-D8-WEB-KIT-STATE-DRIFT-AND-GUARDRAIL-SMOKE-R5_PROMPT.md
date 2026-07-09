# MAIN-CITYBRAIN-D8-WEB-KIT-STATE-DRIFT-AND-GUARDRAIL-SMOKE-R5


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Prove the Web and Kit surfaces are faithful projections of `one_truth_index.json` and preserve the boundary under interaction. Drift is divergence from the bundle authority, not simply disagreement between surfaces.

## Required smoke cases

1. Load `one_truth_index.json`; verify Web projection hash and Kit projection hash match the authoritative refs.
2. Web selects Mobility Access entity; Kit overlay/inspector resolves same entity and both match `one_truth_index.json`.
3. Kit selects/highlights entity; Web evidence panel resolves same refs and both match `one_truth_index.json`.
4. Timeline scrub updates scenario state, trace stage, overlay state, and option context consistently against bundle refs.
5. Track D panel shows eligible packet but no approval/execution is created.
6. Forbidden command attempts are explicitly rejected and logged with `command_status = rejected`, `reason = review_only_boundary`, `execution_state = not_executed`.
7. `execution_state = not_executed` remains visible.
8. Claim labels and limitations remain visible after state changes.
9. Re-run after any patch to catch drift regressions.

## Outputs

```text
WEB_KIT_STATE_DRIFT_REPORT.json
GUARDRAIL_SMOKE_REPORT.json
ONE_TRUTH_REGRESSION_REPORT.json
ONE_TRUTH_AUTHORITY_REPORT.json
NO_ACTION_BOUNDARY_AUDIT.json
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_STATE_DRIFT_AND_GUARDRAIL_SMOKE_R5_WITH_LIMITATIONS`
