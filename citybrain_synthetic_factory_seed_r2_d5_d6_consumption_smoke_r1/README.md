# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1-PACKAGE

Codex-ready package to consume the locked Synthetic Factory Seed R2 Product Consumption R1 output and prove
that the combined synthetic/replay product feeds can be used by bounded D5 runtime packet smoke and D6 local control-room index smoke.

This package is a handoff package, not a result package.

## Input

Expected existing output root:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
```

Required input files:

```text
PRODUCT_CONSUMPTION_R1_DECISION.json
PRODUCT_FEED_MANIFEST_R1.json
WATCH_QUEUE_COMBINED_R1.jsonl
EVENT_REPLAY_COMBINED_R1.jsonl
ASK_FIXTURE_INDEX_R1.jsonl
CHECK_FIXTURE_INDEX_R1.jsonl
BRIEF_FIXTURE_INDEX_R1.jsonl
SPATIAL_OVERLAY_INDEX_R1.jsonl
D5_RUNTIME_PACKET_FIXTURES_R1.jsonl
D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html
BOUNDARY_AND_NO_ACTION_AUDIT_R1.json
SECRET_SCAN_REPORT_R1.json
HASH_MANIFEST.json
```

The input must be consumed read-only. Do not mutate Seed R1, Seed R2, Product Consumption R1, R2/R2A/R2B/R2E, or external raw roots.

## Output

Expected output root:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1
```

Expected result status:

```text
PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS
```

## Boundaries

- Synthetic/replay/donor-context only.
- Not official Dubai truth.
- No human/person-level records.
- No live monitoring claim.
- No dispatch/control/enforcement/legal/certified claim.
- No raw provider payloads.
- No credentials or provider keys.
