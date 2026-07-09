# Founder Probe Review Card: founder-probe-r2-12

## Task Identity

- Task id: `founder-probe-r2-12`
- Family: `mobility_access_interruption_v0`
- Scenario: `contradiction_pair`
- Eval case: `eval-r2:mobility_access_interruption_v0:contradiction_pair`
- CHECK ref: `check:v1:mobility_access_interruption:stress_eval`
- Derived overlays: `derived_overlay:107abd2020814b7c;derived_overlay:60ee3e2f0201d6ac;derived_overlay:fbb74c3aa4879bd8;derived_overlay:b3871caf4eebf5b9;derived_overlay:c99c60d157480194`

## What This Task Tests

Contradiction case: does CHECK surface conflicting evidence and preserve the downgrade/abstain boundary?

## Source / Evidence Summary

```json
{
  "expected_product_claim": "abstain_or_limited",
  "replay_mode": "local_offline_replay",
  "review_packet_id": null,
  "review_packet_source": null,
  "source_class": "replay",
  "source_refs": [
    "source:v1_1:mobility_access_interruption:atlas",
    "diff:v2_5:mobility_access_interruption:long_history"
  ]
}
```

## CER / SEG Context

```json
{
  "cer_entity": null,
  "r1_cer_entity_resolution": null,
  "r1_seg_context": null,
  "raw_id_bypass": false,
  "seg_context": null
}
```

## CHECK v1 Summary

```json
{
  "aggregate_stress_outcome_counts": {
    "candidate_only": 80,
    "contradiction": 80,
    "downgrade_freshness": 80,
    "downgrade_source_class": 80,
    "downgrade_source_depth": 80,
    "sufficient_for_review": 80
  },
  "cannot_claim": [
    "No founder/operator session result is created by this assembler.",
    "No operator fuel, disposition, training row, or learned label is created.",
    "No live ingestion, production monitoring, forecast, or recommendation authority is created.",
    "No official case, ticket, dispatch, control, enforcement, legal finding, or certified finding is created.",
    "No source or canonical truth is mutated.",
    "no source truth correction",
    "no forecast authority",
    "no dispatch/control/enforcement",
    "no training eligibility"
  ],
  "challenge_class": "contradiction",
  "check_ref": "check:v1:mobility_access_int
  ... truncated
}
```

## Event State

```json
{
  "eval_expected_event_handling": "local_replay_state_only",
  "event_fabric_v2_5": {
    "brief_attachment_count": 360,
    "check_attachment_count": 336,
    "event_count": 360,
    "family_id": "mobility_access_interruption",
    "materialized_state_ref": "event_state:v2_5:mobility_access_interruption",
    "spatial_handoff_count": 336,
    "watch_admitted_count": 144
  },
  "incident_plan_state": {}
}
```

## Simulation / Option Context

```json
{
  "eval_expected_handling": "simulation_not_applicable",
  "forecast_created": false,
  "non_sumo_option_context": {},
  "recommendation_authority": "none",
  "simulation_v2_4_comparison": {}
}
```

## BRIEF Summary

```json
{
  "available": true,
  "source": "outputs/main_citybrain_epoch4_trackb_maturity_brief_governance_r1/BRIEF_V3_VARIANTS.json",
  "summary": {
    "no_action_boundary": "review_only_no_action",
    "packet_id": "brief_v3:founder_review:mobility_access_interruption",
    "variant_kinds": [
      "executive",
      "operator",
      "technical"
    ]
  },
  "task_refs": [
    "brief:v3:mobility_access_interruption:operator",
    "brief:v3:mobility_access_interruption:executive",
    "brief:v3:mobility_access_interruption:technical"
  ]
}
```

## Spatial Refs

```json
{
  "event_fabric_v2_5_spatial_handoff_count": 336,
  "incident_spatial": {},
  "review_packet_spatial_refs": null,
  "task_spatial_refs": [
    "spatial:v2_5:mobility_access_interruption:atlas_overlay"
  ]
}
```

## Derived Overlay Summary

```json
[
  {
    "overlay_id": "derived_overlay:107abd2020814b7c",
    "permitted_scope": "derived_overlay_only",
    "promoted_to_canonical_truth": false,
    "promoted_to_source_truth": false,
    "queue": "identity_ambiguity",
    "requires_review": true
  },
  {
    "overlay_id": "derived_overlay:60ee3e2f0201d6ac",
    "permitted_scope": "derived_overlay_only",
    "promoted_to_canonical_truth": false,
    "promoted_to_source_truth": false,
    "queue": "identity_ambiguity",
    "requires_review": true
  },
  {
    "overlay_id": "derived_overlay:fbb74c3aa4879bd8",
    "permitted_scope": "derived_overlay_only",
    "promoted_to_canonical_truth": false,
    "promoted_to_source_truth": false,
    "queue": "identity_ambiguity",
    "requires_review": true
  },
  {
    "overlay_id": "derived_overlay:b3871caf4eebf5b9",
    "permitted_scope": "derived_overlay_only",
    "promot
  ... truncated
}
```

## Missing Evidence Notes

- Review Packet 360 family packet not found for mobility_access_interruption_v0; card uses eval, BRIEF, event fabric, and overlay refs instead.

## Cannot-Claim Block

- No founder/operator session result is created by this assembler.
- No operator fuel, disposition, training row, or learned label is created.
- No live ingestion, production monitoring, forecast, or recommendation authority is created.
- No official case, ticket, dispatch, control, enforcement, legal finding, or certified finding is created.
- No source or canonical truth is mutated.
- no source truth correction
- no forecast authority
- no dispatch/control/enforcement
- no training eligibility

## What You Should Judge

- Is the subject understandable?
- Does the evidence support the stated claim?
- Should the claim be downgraded?
- What evidence is missing?
- Is the BRIEF useful?
- Is CHECK useful?
- Is simulation useful or applicable?
- Is spatial context useful or applicable?
- What should be fixed before showing this to anyone else?

## CSV Row Guidance

Fill the review columns for this exact task in `FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv`.
Keep stable metadata unchanged: `task_id`, `family`, `scenario`, `eval_case`, `check_ref`, `derived_overlays`, `reviewer_id_or_alias`, and `reviewer_type`.

Fields:

- task_id
- family
- scenario
- eval_case
- check_ref
- derived_overlays
- reviewer_id_or_alias
- reviewer_type
- completed_at
- understood_subject
- supports_claim
- should_downgrade
- missing_evidence
- brief_usefulness_1_to_5
- check_usefulness_1_to_5
- simulation_usefulness_1_to_5
- spatial_usefulness_1_to_5
- review_decision
- free_text_notes
