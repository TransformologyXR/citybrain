# MAIN-CITYBRAIN-D8-LIVE-CAPTURE-MEDIA-PASS-PREFLIGHT

## Shared context

Read `00_SHARED_CONTEXT.md` first.

## Task position

Stage 1 of 20 in the D8 post-handoff follow-through sequence.

## Purpose

Confirm D8 handoff is green; locate capture manifests with placeholder `media_ref`; inventory running web companion and Omniverse Kit capture ability; refuse to proceed green if neither surface can be captured.

## Inputs to inspect

- `outputs/main_citybrain_d8_demonstrability_certified_state_handoff`
- Upstream D8 roots referenced by its `D8_CLOSED_TRACK_LEDGER.json`
- Relevant media/viewer/frontend input folders if present
- Existing web companion and Omniverse Kit runtime/source files only as needed for this stage

## Non-negotiable constraints

- No new substrate, city, domain, option-set semantics, perception stack, or simulation capability.
- Do not silently convert placeholder media into real evidence.
- Do not invent viewer sessions, quotes, or scores.
- Do not fabricate M04/M05 baseline/abstain fields.
- Keep Mobility Access corridor as the certified hero spine.
- Preserve local/LAN/replay/review/query-only boundary.
- Preserve `execution_state = not_executed`.
- Track D remains authoritative; do not create approvals/executions.

## Required work

1. Load and validate required upstreams.
2. Produce the stage artifact root under `outputs/main_citybrain_d8_live_capture_media_pass_preflight`.
3. Write JSON decision, validation report, boundary audits, no-action audit, no-mutation audit, secret audit, and hash manifest.
4. Use explicit `PASS_WITH_LIMITATIONS`, `PARTIAL_PENDING_*`, or `FAIL` status according to evidence.
5. Do not stage or commit.

## Required artifacts

- `D8_LIVE_CAPTURE_MEDIA_PASS_PREFLIGHT_DECISION.json`
- `CAPTURE_PLACEHOLDER_INVENTORY.json`
- `CAPTURE_TOOLCHAIN_INVENTORY.json`
- `BOUNDARY_LEDGER.json`
- `HASH_MANIFEST.json`

## Close condition

This stage can be green only when the evidence required by the purpose exists and is hashed. Otherwise it must be honest partial/pending with a concrete missing-evidence ledger.
