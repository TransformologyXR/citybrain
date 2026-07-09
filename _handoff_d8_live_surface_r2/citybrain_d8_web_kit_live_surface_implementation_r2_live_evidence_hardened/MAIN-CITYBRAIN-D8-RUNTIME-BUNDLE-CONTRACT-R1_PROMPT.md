# MAIN-CITYBRAIN-D8-RUNTIME-BUNDLE-CONTRACT-R1


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Create the canonical local runtime bundle contract that both Web and Kit will consume.

## Build

Under `packages/contracts/`, create JSON schemas or documented schema files for:

```text
scenario_state.json
review_state.json
evidence_bundle.json
option_sets.json
trace.jsonl
track_d_packets.json
kit_overlay_packets.json
claim_labels.json
moment_scoreboard.json
limitations.json
one_truth_index.json
bridge_command.json
bridge_event.json
```

Under `packages/fixtures/mobility_access/runtime_bundle/`, create a current bundle derived only from certified outputs.

## Requirements

- Every file has `schema_version`, `scenario_state_ref`, `source_root_refs`, and claim labels where applicable.
- `execution_state = not_executed` is explicit.
- Track D authority is explicit.
- D7 observations remain candidate observations, not findings.
- Missing M04/M05 fields remain documented partial; do not invent baseline/abstain values.
- Hash and lineage index records every source output root used.

## Validation

Create:

```text
RUNTIME_BUNDLE_CONTRACT_REPORT.json
RUNTIME_BUNDLE_VALIDATION_REPORT.json
ONE_TRUTH_INDEX.json
MISSING_FIELD_LEDGER.json
```

Run Python validation over all JSON/JSONL files. If JSON schema tooling is unavailable, implement lightweight validators in a helper script.

## Decision status

`PASS_MAIN_CITYBRAIN_D8_RUNTIME_BUNDLE_CONTRACT_R1_WITH_LIMITATIONS`


## R2 authority requirement

`one_truth_index.json` is the authoritative state spine for this sprint. Every surface projection must resolve back to it.

Add explicit authority metadata:

```json
{
  "authority": "one_truth_index",
  "scenario_state_ref": "...",
  "certified_tip_ref": "main_citybrain_d8_demonstrability_certified_state_handoff",
  "surface_projection_refs": {
    "web": "apps/web-control-room",
    "kit": "apps/kit/citybrain.control_room",
    "bridge": "packages/fixtures/mobility_access/bridge"
  }
}
```

Create `ONE_TRUTH_AUTHORITY_REPORT.json` showing every runtime bundle file is indexed, hashable, and traceable to the certified Mobility Access/D8 outputs. Drift tests later must compare Web and Kit projections to this index, not only to each other.
