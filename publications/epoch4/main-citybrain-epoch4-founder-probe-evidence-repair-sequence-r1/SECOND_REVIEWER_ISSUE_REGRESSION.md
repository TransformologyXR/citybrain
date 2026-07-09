# Second Reviewer Issue Regression

- mobility_cards_have_packet_evidence_or_backfill: `True` - Mobility cards use native packet evidence if present; otherwise derived_review_packet_backfill_not_source_truth is attached.
- mobility_cards_have_cer_seg_context: `True` - CER/SEG context is attached from mobility backfill.
- negative_no_data_actual_outcomes: `True` - No-data cards use challenge boundary actuals.
- stale_freshness_actual_outcomes: `True` - Stale cards use challenge boundary actuals.
- contradiction_explanations: `True` - Contradiction cards explain the conflict and CHECK downgrade/hold behavior.
- non_sumo_families_not_forced_through_sumo: `True` - Existing simulation context remains no-forecast and non-SUMO families are not converted to SUMO claims.
- no_forbidden_capability_language: `True` - Generated guards assert no session/fuel/training/live/forecast/action/source-truth mutation.

Mobility native Review Packet 360 remains absent, so R3 uses `derived_review_packet_backfill_not_source_truth` and keeps the limitation visible.
