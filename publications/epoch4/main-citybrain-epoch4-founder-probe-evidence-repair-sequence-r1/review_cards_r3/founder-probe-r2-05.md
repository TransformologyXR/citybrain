# Founder Probe Review Card R3: founder-probe-r2-05

## Task Identity

- Task id: `founder-probe-r2-05`
- Family: `city_asset_infrastructure_issue`
- Scenario: `positive_packet_baseline`
- Eval case: `eval-r2:city_asset_infrastructure_issue:positive_packet_baseline`
- CHECK ref: `check:v1:city_asset_infrastructure_issue:stress_eval`
- Derived overlays: ``

## R3 Evidence Repair Summary

```json
{
  "backfill_label": null,
  "evidence_packet": {
    "all_required_sections_present": true,
    "brief_v3_variant_refs": [
      "brief:v3:city_asset_infrastructure_issue:operator",
      "brief:v3:city_asset_infrastructure_issue:executive",
      "brief:v3:city_asset_infrastructure_issue:technical"
    ],
    "cannot_claim": [
      "official action",
      "case/ticket",
      "dispatch/control/enforcement",
      "product forecast",
      "session result"
    ],
    "cer_entity": "cer:city_asset_infrastructure_issue:primary",
    "check_v1_result_ref": "check:v1:city_asset_infrastructure_issue:simulation_v2_4",
    "data_maturity_refs": [
      "outputs/main_citybrain_epoch4_data_maturity_diagnostic_product_r2/DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json"
    ],
    "diff_source_refresh_refs": [
      "diff:v2_4:city_asset_infrastructure_issue:history_delta"
    ],
    "event_state_ref": "event_state:v2_4:city_asset_infrastructure_issue",
    "family_id": "city_asset_infrastructure_issue",
    "limitations": [
      "internal packet only",
      "no founder rev
  ... truncated
}
```

## CER / SEG Context

```json
{
  "cer_context": {
    "cer_entity": "cer:city_asset_infrastructure_issue:primary",
    "cer_entity_resolution": null
  },
  "cer_context_missing": false,
  "context_source": "review_packet_360_v2",
  "seg_context": {
    "seg_context": "seg:city_asset_infrastructure_issue:context",
    "seg_context_r1": null
  },
  "seg_context_missing": false,
  "status": "attached"
}
```

## Actual vs Expected Outcome

```json
{
  "actual_outcome_limitations": [
    "Direct harness CHECK assertion is mapped from the closest eval harness scenario."
  ],
  "actual_outcome_match_status": "matched_direct_check_harness",
  "actual_outcome_source_artifact": "outputs/main_citybrain_epoch4_product_loop_eval_harness_execution_r1/CHECK_ASSERTION_RESULTS.json",
  "challenge_boundary_evidence": {},
  "expected_check_outcome": "sufficient_for_review",
  "matched_actual_boundary": true,
  "matched_actual_check_outcome": "sufficient_for_review"
}
```

## Human-Readable Explanation

### What This Case Is Testing

Positive packet baseline: can a bounded local/replay packet be understood and reviewed without over-claiming truth?

### What CityBrain Can Say

The expected CHECK outcome is sufficient_for_review; matched actual outcome is sufficient_for_review.

### Why CHECK Passed / Downgraded / Abstained / Held

The case tests whether a baseline packet is understandable and review-limited without crossing into official action or forecast authority.

### What Evidence Is Missing

- None recorded.

### What The Founder Should Judge

- Is the subject understandable?
- Does the evidence support the stated review-limited claim?
- Should the claim be downgraded or held?
- What evidence is missing before any external use?
- Are CHECK, BRIEF, simulation/option context, and spatial context useful?

## Original R2 Source / Evidence Summary

```json
{
  "expected_product_claim": "review_limited_positive",
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
    "Review Packet 360: dispatch/control/enforcement",
    "Review Packet 360: product forecast",
    "Review Packet 360: session result"
  ],
  "challenge_class": "positive",
  "check_ref": "check:v1:cit
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

## Cannot-Claim Block

- No founder/operator session result is created by this repair sequence.
- No operator fuel, disposition, training row, or learned label is created.
- No live ingestion, production monitoring, forecast, or recommendation authority is created.
- No official case, ticket, dispatch, control, enforcement, legal finding, or certified finding is created.
- No source or canonical truth is mutated.
- No founder/operator session result is created by this assembler.
- no source truth correction
- no forecast authority
- no dispatch/control/enforcement
- no training eligibility
- Review Packet 360: official action
- Review Packet 360: case/ticket
- Review Packet 360: dispatch/control/enforcement
- Review Packet 360: product forecast
- Review Packet 360: session result

## CSV Row Guidance

Fill only the blank review columns in `FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED_R3.csv` after reading this R3 card. Do not change stable metadata columns.
