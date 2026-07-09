# Founder Probe Review Card: founder-probe-r2-06

## Task Identity

- Task id: `founder-probe-r2-06`
- Family: `city_asset_infrastructure_issue`
- Scenario: `negative_no_data`
- Eval case: `eval-r2:city_asset_infrastructure_issue:negative_no_data`
- CHECK ref: `check:v1:city_asset_infrastructure_issue:stress_eval`
- Derived overlays: ``

## What This Task Tests

Negative no-data case: does the packet abstain or stay limited when evidence is absent?

## Source / Evidence Summary

```json
{
  "expected_product_claim": "abstain_or_limited",
  "replay_mode": "local_offline_replay",
  "review_packet_id": "city_asset_infrastructure_issue",
  "review_packet_source": "review_packet_360_v2_by_family",
  "source_class": "replay",
  "source_refs": [
    "source:v1_1:city_asset_infrastructure_issue:atlas",
    "diff:v2_5:city_asset_infrastructure_issue:long_history",
    "source:v1_1:city_asset_infrastructure_issue:v2_packet"
  ]
}
```

## CER / SEG Context

```json
{
  "cer_entity": "cer:city_asset_infrastructure_issue:primary",
  "r1_cer_entity_resolution": null,
  "r1_seg_context": null,
  "raw_id_bypass": false,
  "seg_context": "seg:city_asset_infrastructure_issue:context"
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
    "no training eligibility",
    "Review Packet 360: official action",
    "Review Packet 360: case/ticket",
    "R
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
    "family_id": "city_asset_infrastructure_issue",
    "materialized_state_ref": "event_state:v2_5:city_asset_infrastructure_issue",
    "spatial_handoff_count": 336,
    "watch_admitted_count": 144
  },
  "incident_plan_state": {
    "event_fabric_v2_1_ref": "outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening/EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json",
    "event_state_ref": "event_state:v2_1:city_asset_infrastructure_issue",
    "state": "review_required"
  }
}
```

## Simulation / Option Context

```json
{
  "eval_expected_handling": "SUMO_smoke_allowed_not_calibrated",
  "forecast_created": false,
  "non_sumo_option_context": {},
  "recommendation_authority": "none",
  "simulation_v2_4_comparison": {
    "baseline_avg_duration": 21.0,
    "baseline_option": "normal_corridor",
    "duration_delta_seconds": 10.6,
    "family_id": "city_asset_infrastructure_issue",
    "forecast_created": false,
    "intervention_option": "restricted_asset_corridor",
    "option_avg_duration": 31.6,
    "recommendation_authority": "none",
    "runner": "SUMO_local_smoke"
  }
}
```

## BRIEF Summary

```json
{
  "available": true,
  "source": "outputs/main_citybrain_epoch4_incident_plan_three_family_product_loop_r1/BRIEF_V3_PACKETS_BY_FAMILY.json",
  "summary": {
    "brief_ref": "brief_v3:city_asset_infrastructure_issue:review_packet",
    "brief_v3_source": "outputs/main_citybrain_track6_brief_v3_export_hardening/BRIEF_V3_EXPORT_PACKET.json",
    "official_report_created": false
  },
  "task_refs": [
    "brief:v3:city_asset_infrastructure_issue:operator",
    "brief:v3:city_asset_infrastructure_issue:executive",
    "brief:v3:city_asset_infrastructure_issue:technical"
  ]
}
```

## Spatial Refs

```json
{
  "event_fabric_v2_5_spatial_handoff_count": 336,
  "incident_spatial": {
    "cer_entity_refs": [
      "cer:asset:infrastructure_candidate"
    ],
    "live_control_claim": false,
    "spatial_packet_ref": "spatial_overlay:city_asset_infrastructure_issue:incident_plan"
  },
  "review_packet_spatial_refs": [
    "spatial:v2_4:city_asset_infrastructure_issue:review_packet"
  ],
  "task_spatial_refs": [
    "spatial:v2_5:city_asset_infrastructure_issue:atlas_overlay"
  ]
}
```

## Derived Overlay Summary

```json
[]
```

## Missing Evidence Notes

- None recorded.

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
- Review Packet 360: official action
- Review Packet 360: case/ticket
- Review Packet 360: dispatch/control/enforcement
- Review Packet 360: product forecast
- Review Packet 360: session result

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
