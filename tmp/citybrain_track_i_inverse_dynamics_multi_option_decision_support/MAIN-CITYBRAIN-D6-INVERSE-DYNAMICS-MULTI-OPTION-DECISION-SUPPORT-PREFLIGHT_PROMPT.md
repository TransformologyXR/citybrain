# Prompt — MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-DECISION-SUPPORT-PREFLIGHT

## Task

Create the preflight for inverse-dynamics multi-option decision support.

## Goal

Define how CityBrain will search from a desired review-safe outcome back to a bounded set of human-reviewable candidate options for the shared hero corridor scenario.

This preflight must prove readiness only. It must not generate final option sets, run new simulations, or promote any proposal.

## Required upstreams

Find and validate:

- `MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH`
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE`

If any required upstream is missing or not green, fail safely.

## Preflight design requirements

Produce:

1. inverse-dynamics scope statement
2. shared hero scenario binding
3. desired-outcome contract
4. candidate-action search-space contract
5. dependency map to Track S/B/R/D
6. option/proposal boundary statement
7. no-execution/no-action boundary statement
8. golden quality gate reuse plan
9. generator safety constraints
10. closeout acceptance plan

## Candidate action search space

Use only review-safe candidate action types from the Track S/hero corridor enum, for example:

- `do_nothing_monitor`
- `review_reroute_option`
- `review_signal_timing_option`
- `review_lane_access_option`
- `review_crew_schedule_option`
- `review_kerbside_access_option`
- `review_public_information_draft`
- `review_site_visit_request`
- `escalate_to_human_operator`

Explicitly block:

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

## Expected output root

`outputs/main_citybrain_d6_inverse_dynamics_multi_option_decision_support_preflight/`

## Expected files

- `MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_DECISION_SUPPORT_PREFLIGHT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `INVERSE_DYNAMICS_PREFLIGHT_SCOPE.md`
- `SHARED_HERO_SCENARIO_BINDING.json`
- `DESIRED_OUTCOME_CONTRACT.json`
- `CANDIDATE_ACTION_SEARCH_SPACE.json`
- `TRACK_S_B_R_D_DEPENDENCY_MAP.json`
- `OPTION_PROPOSAL_BOUNDARY.md`
- `GENERATOR_SAFETY_CONSTRAINTS.json`
- `QUALITY_GATE_REUSE_PLAN.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Pass status

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_DECISION_SUPPORT_PREFLIGHT_WITH_LIMITATIONS`

## Fail status

`FAIL_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_DECISION_SUPPORT_PREFLIGHT`
