# MAIN-CITYBRAIN-D14-STAGED-ROUTER-SCHEMA-PREFLIGHT-R1

## Goal
Verify D14 should move from flat route taxonomy to staged router schema, and collect the required inputs.

## Required inputs
- Assembled synthetic corpus v0, 150 rows.
- Latest v0.4B relabeled corpus.
- v0.4B comparison/audit/gate results.
- v0.4A subject-answer decision artifacts.
- Prior double-label independent label files if needed for history.

## Checks
- Confirm v0.4B failed: exact route disagreement > 15% or boundary gates failed.
- Confirm no Split/Seal R3 has run.
- Confirm router preflight/training has not opened.
- Confirm synthetic rows preserve `source_type = synthetic_v0_clean_ai`.
- Confirm real operator validation remains unclaimed.

## Output
Write:
- `D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_DECISION.json`
- `D14_STAGED_ROUTER_SCHEMA_INPUT_INVENTORY.json`

## Status
- `PASS_D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_R1`
- or `BLOCKED_D14_STAGED_ROUTER_SCHEMA_PREFLIGHT_MISSING_INPUTS`
