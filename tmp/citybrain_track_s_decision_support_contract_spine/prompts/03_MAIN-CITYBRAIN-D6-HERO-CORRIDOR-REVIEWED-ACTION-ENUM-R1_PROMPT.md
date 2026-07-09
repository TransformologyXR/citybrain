# PROMPT — MAIN-CITYBRAIN-D6-HERO-CORRIDOR-REVIEWED-ACTION-ENUM-R1

You are Codex continuing CityBrain Track S after the option-set contract and 9-stage interface preflights.

## Task

Create the hero corridor reviewed-action enum R1.

Task name:

`MAIN-CITYBRAIN-D6-HERO-CORRIDOR-REVIEWED-ACTION-ENUM-R1`

Expected status on success:

`PASS_MAIN_CITYBRAIN_D6_HERO_CORRIDOR_REVIEWED_ACTION_ENUM_R1_WITH_LIMITATIONS`

Expected output root:

`outputs/main_citybrain_d6_hero_corridor_reviewed_action_enum_r1/`

Expected runner:

`scripts/run_main_citybrain_d6_hero_corridor_reviewed_action_enum_r1.py`

## Purpose

Define the bounded action-type search space for the shared hero corridor scenario before inverse dynamics or Plan Mode uses it.

This is required because inverse dynamics cannot search for reviewed options without a closed review-safe candidate-action enum.

## Shared scenario

Use the same hero scenario family already frozen in R2:

- bounded LON hero neighbourhood / corridor replay context
- construction lane-blockage / corridor event context
- same event/route story used by Hero USD Twin, HITL proposal, and future Plan Mode/SUMO
- local/replay review-only context

## Required allowed review-only action types

Define a closed enum of review-safe action types. Suggested minimum:

- `do_nothing_monitor`
- `review_reroute_option`
- `review_signal_timing_option`
- `review_lane_access_option`
- `review_crew_schedule_option`
- `review_kerbside_access_option`
- `review_public_information_draft`
- `review_site_visit_request`
- `escalate_to_human_operator`

All are review proposals only. None is execution.

## Required blocked action types

Define a blocked enum including at least:

- `auto_execute`
- `dispatch_team`
- `change_signal_live`
- `enforce_violation`
- `issue_ticket`
- `publish_public_alert`
- `reroute_live_traffic`
- `control_asset`
- `legal_determination`
- `certify_incident`
- `certify_twin_geometry`
- `create_official_case`

## Required mapping

For each allowed action type define:

- option eligibility
- required evidence refs
- required graph refs
- required simulation refs if applicable
- whether it can be promoted to Track D proposal
- Track D proposal type mapping
- default review state
- allowed comparison axes
- boundary limitations

## Expected files

- `MAIN_CITYBRAIN_D6_HERO_CORRIDOR_REVIEWED_ACTION_ENUM_R1_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `HERO_CORRIDOR_REVIEWED_ACTION_ENUM.json`
- `BLOCKED_ACTION_ENUM.json`
- `ACTION_TO_OPTION_SET_MAPPING.json`
- `ACTION_TO_TRACK_D_PROPOSAL_MAPPING.json`
- `ACTION_BOUNDARY_RULES.json`
- `ACTION_ENUM_VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Validation

Pass only if:

- Allowed action enum exists and is closed.
- Blocked action enum exists and blocks unsafe/autonomous/control/legal actions.
- Every allowed action remains review-only.
- Every allowed action maps to option-set semantics.
- Track D proposal ownership is preserved.
- No execution state other than `not_executed` is introduced.
- Audits pass.
