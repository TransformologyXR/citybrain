# ASK v1.1 Real Corpus Eval R2 Mapping Changes

## Summary

- Cases newly mapped: 8
- Cases still needing mapping: 0
- Contradiction case status: `waived_no_retained_same_claim_pair`

## Newly Mapped Cases

### real-corpus-002-entity-profile-ev-asset-87

- Family: `entity_profile`
- Source artifact: `packages/fixtures/london_mobility_source_records/source_record_bundle.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: known retained source row plus unknowns/cannot_claim for live availability and certification

### real-corpus-003-subject-answer-wood-lane-support

- Family: `subject_answer`
- Source artifact: `packages/fixtures/brain_surface_story_queue/primary_story_queue.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: answer retained support only and preserve proximity-not-causality

### real-corpus-004-source-record-profile-tims-219173

- Family: `source_record_profile`
- Source artifact: `packages/fixtures/story_first_demo/story_source_bundle.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: profile the retained source record and cite replay/source timestamp limits

### real-corpus-005-patch-queue-story-review-items

- Family: `patch_queue_query`
- Source artifact: `packages/fixtures/brain_surface_story_queue/primary_story_queue.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: list/count review items only; not mutate review state

### real-corpus-007-no-data-missing-tims-record

- Family: `no_data`
- Source artifact: `packages/fixtures/story_first_demo/story_source_bundle.json`
- Adapter mapping: `r2_negative_or_external_gap_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: first-class no_data with safe next look

### real-corpus-011-staleness-tfl-replay-record

- Family: `staleness`
- Source artifact: `packages/fixtures/story_first_demo/story_source_bundle.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: stale/freshness warning if source timestamp is older than R1 policy; never live claim

### real-corpus-013-selected-item-followup-ev-asset

- Family: `selected_item_followup`
- Source artifact: `packages/fixtures/london_mobility_source_records/source_record_bundle.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: selected item anchors the query without raw_query downstream

### real-corpus-019-renderer-no-undowngrade-wood-lane

- Family: `renderer_no_undowngrade`
- Source artifact: `packages/fixtures/story_first_demo/story_source_bundle.json`
- Adapter mapping: `r2_mapped_by_eval_adapter`
- Original readiness: `needs_mapping`
- Expected behavior: render degradation if wording upgrades proximity to confirmed impact

## Still Needs Mapping

No non-waived cases still need mapping.

## Waived

- `real-corpus-010-contradiction-retained-source-gap` (`contradiction`): waived_no_retained_same_claim_pair

## Contradiction Waiver

No valid retained same-claim contradiction pair was found during scout. Contradiction remains covered by sealed fixture eval and is waived from real-corpus R2 until a genuine retained conflict pair appears.
