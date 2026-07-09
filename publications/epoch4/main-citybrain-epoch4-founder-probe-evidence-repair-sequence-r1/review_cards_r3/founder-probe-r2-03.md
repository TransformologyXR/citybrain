# Founder Probe Review Card R3: founder-probe-r2-03

## Task Identity

- Task id: `founder-probe-r2-03`
- Family: `building_compliance_perception_candidate`
- Scenario: `stale_freshness`
- Eval case: `eval-r2:building_compliance_perception_candidate:stale_freshness`
- CHECK ref: `check:v1:building_compliance_perception_candidate:stress_eval`
- Derived overlays: ``

## R3 Evidence Repair Summary

```json
{
  "backfill_label": null,
  "evidence_packet": {
    "all_required_sections_present": true,
    "brief_v3_variant_refs": [
      "brief:v3:building_compliance_perception_candidate:operator",
      "brief:v3:building_compliance_perception_candidate:executive",
      "brief:v3:building_compliance_perception_candidate:technical"
    ],
    "cannot_claim": [
      "official action",
      "case/ticket",
      "dispatch/control/enforcement",
      "product forecast",
      "session result"
    ],
    "cer_entity": "cer:building_compliance_perception_candidate:primary",
    "check_v1_result_ref": "check:v1:building_compliance_perception_candidate:simulation_v2_4",
    "data_maturity_refs": [
      "outputs/main_citybrain_epoch4_data_maturity_diagnostic_product_r2/DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json"
    ],
    "diff_source_refresh_refs": [
      "diff:v2_4:building_compliance_perception_candidate:history_delta"
    ],
    "event_state_ref": "event_state:v2_4:building_compliance_perception_candidate",
    "family_id": "building_compliance_perception_candidate",
  ... truncated
}
```

## CER / SEG Context

```json
{
  "cer_context": {
    "cer_entity": "cer:building_compliance_perception_candidate:primary",
    "cer_entity_resolution": null
  },
  "cer_context_missing": false,
  "context_source": "review_packet_360_v2",
  "seg_context": {
    "seg_context": "seg:building_compliance_perception_candidate:context",
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
    "Challenge suite records observed boundary and forbidden-capability guard fields, not a full standalone CHECK report payload."
  ],
  "actual_outcome_match_status": "matched_challenge_boundary",
  "actual_outcome_source_artifact": "outputs/main_citybrain_epoch4_product_loop_challenge_negative_suite_r1/CHALLENGE_RUN_RESULTS.json",
  "challenge_boundary_evidence": {
    "case_id": "eval-r2:building_compliance_perception_candidate:stale_freshness",
    "expected_check_outcome": "downgrade_freshness",
    "family_id": "building_compliance_perception_candidate",
    "observed_boundary": "PASS_LIMITED_OR_ABSTAIN",
    "official_action_created": false,
    "product_claim_confident": false,
    "simulation_forced_when_not_applicable": false,
    "status": "PASS"
  },
  "expected_check_outcome": "downgrade_freshness",
  "matched_actual_boundary": "PASS_LIMITED_OR_ABSTAIN",
  "matched_actual_check_outcome": "PASS_LIMITED_OR_ABSTAIN"
}
```

## Human-Readable Explanation

### What This Case Is Testing

Freshness downgrade case: does CHECK make stale evidence visible and prevent over-claiming?

### What CityBrain Can Say

The expected CHECK outcome is downgrade_freshness; the actual run preserved boundary PASS_LIMITED_OR_ABSTAIN.

### Why CHECK Passed / Downgraded / Abstained / Held

The case tests whether stale evidence is downgraded instead of treated as current operational truth.

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
  "expected_product_claim": "abstain_or_limited",
  "replay_mode": "local_offline_replay",
  "review_packet_id": "building_compliance_perception_candidate",
  "review_packet_source": "review_packet_360_v2_by_family",
  "source_class": "replay",
  "source_refs": [
    "source:v1_1:building_compliance_perception_candidate:atlas",
    "diff:v2_5:building_compliance_perception_candidate:long_history",
    "source:v1_1:building_compliance_perception_candidate:v2_packet"
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
  "challenge_class": "stale",
  "check_ref": "check:v1:buildi
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
    "family_id": "building_compliance_perception_candidate",
    "materialized_state_ref": "event_state:v2_5:building_compliance_perception_candidate",
    "spatial_handoff_count": 336,
    "watch_admitted_count": 144
  },
  "incident_plan_state": {
    "event_fabric_v2_1_ref": "outputs/main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening/EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json",
    "event_state_ref": "event_state:v2_1:building_compliance_perception_candidate",
    "state": "review_required"
  }
}
```

## Simulation / Option Context

```json
{
  "eval_expected_handling": "simulation_not_applicable",
  "forecast_created": false,
  "non_sumo_option_context": {
    "baseline_option": {
      "option_id": "baseline_review_only",
      "risk": "evidence gaps remain visible",
      "score": 0.42,
      "why": "preserves current bounded review posture"
    },
    "best_review_option": {
      "option_id": "targeted_perception_evidence_review",
      "risk": "still not a finding",
      "score": 0.68,
      "why": "focuses review on perception conflict and source-class weakness"
    },
    "family_id": "building_compliance_perception_candidate"
  },
  "recommendation_authority": "none",
  "simulation_v2_4_comparison": {
    "baseline_option": "no_extra_review",
    "family_id": "building_compliance_perception_candidate",
    "forecast_created": false,
    "intervention_option": "targeted_evidence_review",
    "recommendation_authority": "none",
    "runner": "fixture_grade_non_sumo"
  }
}
```

## BRIEF Summary

```json
{
  "available": true,
  "source": "outputs/main_citybrain_epoch4_incident_plan_three_family_product_loop_r1/BRIEF_V3_PACKETS_BY_FAMILY.json",
  "summary": {
    "brief_ref": "brief_v3:building_compliance_perception_candidate:review_packet",
    "brief_v3_source": "outputs/main_citybrain_track6_brief_v3_export_hardening/BRIEF_V3_EXPORT_PACKET.json",
    "official_report_created": false
  },
  "task_refs": [
    "brief:v3:building_compliance_perception_candidate:operator",
    "brief:v3:building_compliance_perception_candidate:executive",
    "brief:v3:building_compliance_perception_candidate:technical"
  ]
}
```

## Spatial Refs

```json
{
  "event_fabric_v2_5_spatial_handoff_count": 336,
  "incident_spatial": {
    "cer_entity_refs": [
      "cer:building:alpha",
      "cer:observation:near_alpha"
    ],
    "live_control_claim": false,
    "spatial_packet_ref": "spatial_overlay:building_compliance_perception_candidate:incident_plan"
  },
  "review_packet_spatial_refs": [
    "spatial:v2_4:building_compliance_perception_candidate:review_packet"
  ],
  "task_spatial_refs": [
    "spatial:v2_5:building_compliance_perception_candidate:atlas_overlay"
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
