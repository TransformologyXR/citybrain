# MAIN-CITYBRAIN-D8-LOCAL-BRIDGE-AND-ONE-TRUTH-SYNC-R3


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Create a local bridge and one-truth synchronization protocol between Web and Kit using the canonical runtime bundle. `one_truth_index.json` is the single authority; Web, Kit, trace, Track D, claim labels, and bridge state are projections that must match it.

## Build

Prefer a file-watched JSON/JSONL bridge first because it is offline, transparent, and easy to audit. WebSocket may be added only if dependency-free or already supported.

Create:

```text
packages/contracts/bridge_command.schema.json
packages/contracts/bridge_event.schema.json
packages/fixtures/mobility_access/bridge/inbox/
packages/fixtures/mobility_access/bridge/outbox/
packages/fixtures/mobility_access/bridge/audit/bridge_audit.jsonl
scripts/run_main_citybrain_d8_local_bridge_smoke.py
```

Allowed commands:
`select`, `scrub`, `inspect`, `camera`, `capture`, `focus`, `highlight`, `clear_highlight`.

Forbidden commands:
`execute`, `dispatch`, `route`, `enforce`, `approve`, `create_ticket`, `create_case`, `send_alert`, `control_signal`, `legal_find`, `certify_finding`.

## Required tests

- Allowed command round-trip smoke.
- Forbidden command rejection smoke.
- Bridge audit log contains both allowed and rejected samples.
- Web and Kit consume the same `scenario_state_ref`.
- Drift detector compares Web state, Kit overlay state, trace state, Track D packet state, bridge state, and claim labels **against `one_truth_index.json` as authority**. Web and Kit agreeing with each other is insufficient if both diverge from the bundle.

## Outputs

```text
LOCAL_BRIDGE_CONTRACT_REPORT.json
ONE_TRUTH_SYNC_REPORT.json
ONE_TRUTH_AUTHORITY_REPORT.json
FORBIDDEN_COMMAND_REJECTION_REPORT.json
BRIDGE_AUDIT.jsonl
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_LOCAL_BRIDGE_AND_ONE_TRUTH_SYNC_R3_WITH_LIMITATIONS`
