# Codex handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH

## Goal

Consume the locked Synthetic Factory Dubai Seed R1 and the locked R2E keyed mobility depth pull as **read-only inputs**.
Produce a Seed R2 mobility-depth refresh addendum that deepens product fixtures using LTA/TfL donor/context distributions.

## Inputs

Required:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1`
- `outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL`

Optional for cross-lineage checks:

- `outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE`
- `C:\data\citybrainaw\keyed_mobility_r2e` as external raw root, read-only and not packaged.

## Required outputs

- `SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_DECISION.json`
- `R2_INPUT_READONLY_LINEAGE.json`
- `MOBILITY_DEPTH_DONOR_SUMMARY_R2.json`
- `MOBILITY_DISTRIBUTION_PROFILE_R2.json`
- `EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl`
- `WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl`
- `ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl`
- `CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl`
- `BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl`
- `SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl`
- `FACTORY_VALIDATION_REPORT_R2.json`
- `BOUNDARY_AND_NO_ACTION_AUDIT_R2.json`
- `SECRET_SCAN_REPORT_R2.json`
- `HASH_MANIFEST.json`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

- R1 and R2E are consumed read-only.
- Seed R1 truth/status is not mutated or relabelled.
- R2E LTA/TfL feeds remain donor/context only and not Dubai truth.
- Every generated record has `source_class`, `truth_layer`, `donor_refs`, `evidence_refs`, and `limitation_refs`.
- Every Event Fabric row is local/replay-only.
- WATCH/ASK/CHECK/BRIEF/SPATIAL fixtures parse clean.
- CHECK fixtures explicitly reject live/Dubai/action/certified claims.
- No credentials, raw provider payloads, or failed provider bodies are packaged.
- No human/person-level records.
- No dispatch/control/enforcement/legal/certified claim.
- Exact secret scans pass across package, output root, and external raw roots.

## Run notes

R2E may include empty-valid responses, fail-closed optional endpoints, and one SDK key-present-not-used entry.
Those should be preserved in donor summary but should not block the refresh if the depth pull status is already PASS with limitations.

The refresh should generate a new addendum output root only. Do not edit Seed R1 files.
