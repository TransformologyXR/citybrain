# MAIN-CITYBRAIN-D14-TEMPLATE-GAP-REGISTRY-V02-R1

Using the v0.2 route taxonomy, convert generic gaps into a ranked template-gap registry.

Inputs:
- Prior `CORPUS_V0_TEMPLATE_GAP_REPORT.json`
- Full 150-row preliminary labeled corpus
- v0.2 taxonomy contract

Required outputs:
- `TEMPLATE_GAP_REGISTRY_V02.json`
- `TEMPLATE_GAP_REGISTRY_V02.md`

Rules:
1. Do not use `gap:general operator question needs taxonomy review`.
2. Every gap must be specific and product-actionable.
3. Each gap must include:
   - gap_id
   - examples
   - count
   - probable consuming artifact: WATCH query / ASK template / CHECK rule / UI help / review workspace feature
   - priority
   - whether it blocks router V0 or can be routed to honest unsupported/help response

Expected gap families include:
- source_record_360_needed
- evidence_gap_template_needed
- patch_queue_filter_by_city
- patch_queue_open_count
- patch_queue_update_date_comparison
- external_sharing_guidance
- local_note_visibility_guidance
- human_review_timestamp_status
- weather_context_for_patch_area
- charging_site_source_depth_scan

If a gap is frequent enough, recommend adding a deterministic template before router training.
