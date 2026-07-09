# CityBrain D8 — Source Record Gap Closure & Scenario Coherence

Purpose: close the three remaining source-record blockers from `PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_MILESTONE_FREEZE_WITH_LIMITATIONS`, and verify whether the London/Chicago/Helsinki source-record cards form a coherent human-facing city story or are only supporting source examples.

Current validated state:
- D8 source-record UI integration is green with limitations.
- Default web UI has 27 source-backed cards: 10 London mobility records, 5 Chicago similar-case records, 12 Helsinki visual-entity records.
- Remaining blocker cards: M13 candidate observation source detail, M07 guardrail refusal review-log record, M08 human-review stop record.
- External viewer validation remains false until blockers are resolved or explicitly accepted as known gaps.
- Kit runtime remains unavailable unless separately rechecked.

Non-negotiable boundary:
- local/LAN/replay/review/query context only.
- no production/public API claim.
- no live monitoring/alerts.
- no dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action.
- Track D remains authoritative for proposal lifecycle.
- CityBrain fixture refs do not count as city source records.
- No facts may be invented to fill missing city records.

Key correction:
A source-backed card is not enough if it is not coherent with the demo story. London EV charging points, Chicago violations, and Helsinki buildings may be valid source records, but the UI must not imply they are the same incident/corridor unless the source bundle proves the linkage.
