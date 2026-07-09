# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1

## Objective

Create the first product-consumption layer from the locked synthetic factory seeds.

This should be a **read-only consumption task**, not another data-generation or acquisition task.

## Inputs

- Seed R1: `PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS`
- Seed R2: `PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS`

## Required behavior

1. Consume Seed R1 read-only.
2. Consume Seed R2 read-only.
3. Preserve Seed R1 and Seed R2 decision/status files unchanged.
4. Combine Seed R1 + Seed R2 feeds into product-facing fixture indexes.
5. Ensure Seed R2 mobility-depth rows remain donor/context-only and not Dubai truth.
6. Emit a D5 runtime packet fixture pack suitable for local served-runtime smoke.
7. Emit a D6 local open index HTML that links/labels the product fixtures.
8. Emit boundary/no-action audit and secret scan report.
9. Package only output manifests/fixtures/indexes, not raw provider payloads.

## Output root

`outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1`

## Required outputs

- `PRODUCT_CONSUMPTION_R1_DECISION.json`
- `PRODUCT_FEED_MANIFEST_R1.json`
- `WATCH_QUEUE_COMBINED_R1.jsonl`
- `EVENT_REPLAY_COMBINED_R1.jsonl`
- `ASK_FIXTURE_INDEX_R1.jsonl`
- `CHECK_FIXTURE_INDEX_R1.jsonl`
- `BRIEF_FIXTURE_INDEX_R1.jsonl`
- `SPATIAL_OVERLAY_INDEX_R1.jsonl`
- `D5_RUNTIME_PACKET_FIXTURES_R1.jsonl`
- `D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html`
- `BOUNDARY_AND_NO_ACTION_AUDIT_R1.json`
- `SECRET_SCAN_REPORT_R1.json`
- `HASH_MANIFEST.json`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

- All JSON/JSONL outputs parse clean.
- Seed R1 and Seed R2 consumed read-only.
- WATCH/ASK/CHECK/BRIEF/SPATIAL and Event Fabric product feeds emitted.
- D5 runtime packet fixtures generated from those feeds.
- D6 control-room local index generated.
- No credentials written.
- No raw provider payloads packaged.
- No human/person-level data.
- No LTA/TfL/OPSD donor feed treated as Dubai truth.
- No Overture/OSM/Microsoft seed geometry treated as official Dubai identity.
- No production/live monitoring claim.
- No dispatch/control/enforcement/legal/certified claim.
