# CityBrain D9 — Data Scout Collated Summary

Generated: 2026-07-02  
Inputs validated:
- `main_citybrain_d9_data_scout_closeout.zip`
- `main_citybrain_d9_broad_data_scout_closeout.zip`

## Validation summary

### Narrow D9 data scout
- Status: `PASS_MAIN_CITYBRAIN_D9_DATA_SCOUT_CLOSEOUT_WITH_LIMITATIONS`
- Decision: `GO_D9_ASK_WATCH_BRIEF_WITH_LIMITATIONS`
- JSON parse: 11 / 11 clean
- Hash manifest: 13 / 13 verified after normalizing the `outputs/` prefix
- Audits: claim boundary PASS, no-action PASS, no-mutation PASS, secret PASS
- Ready now: `ASK`, `WATCH`, `BRIEF`, `CHECK`
- Partial: `RECALL`, `DIFF`
- Blocked: none
- Source gaps: 8

### Broad D9 data scout
- Status: `PASS_MAIN_CITYBRAIN_D9_BROAD_DATA_SCOUT_MILESTONE_FREEZE_WITH_LIMITATIONS`
- Recommendation: `SPLIT_D9_INTO_ASK_WATCH_BRIEF_AND_CHECK_DIFF`
- JSON parse: 9 / 9 clean in closeout ZIP; nested validation package parsed successfully
- Hash manifests: closeout 6 / 6 verified; milestone freeze 8 / 8 verified
- Product opportunities: 15
- Strong: 9
- Partial: 3
- Weak/deferred: 3
- Mode counts: Ask 4, Watch 3, Brief 2, Check 2, Recall 1, Diff 1, Visual 1, Perception 1

## Reconciled decision

Run D9 as a scoped product-mode implementation:

`ASK + WATCH + BRIEF + CHECK`, with `RECALL` as a bounded cutaway.

Do **not** build `DIFF` or `PERCEPTION/VSS` in this implementation sprint. They remain deferred until snapshot cadence, licensed media, and source-detail gates are stronger.

## Product-mode readiness

| Mode | Status | What it can surface now | Limitation |
|---|---|---|---|
| ASK | Ready with limitations | Cited answers for London Wood Lane, NYC MVC cascade, selected cartridge contexts, uncertainty questions | Must cite records/limitations; no free-form unsupported answer |
| WATCH | Ready with limitations | Manual-review queue candidates from named queries | Not live monitoring or alerting |
| BRIEF | Ready with limitations | Evidence-backed brief packets for London Wood Lane and NYC MVC cascade | Briefs are review context, not recommendations |
| CHECK | Ready | Source-depth, claim-boundary, limitation, no-action checks | Coverage depends on upstream artifacts carrying limitations |
| RECALL | Cutaway / partial | Chicago precedent memory and similar-case examples | Match reasons must be specific; no causality/instruction |
| DIFF | Deferred / partial | Snapshot/package differences only | No reliable temporal source cadence yet |
| VISUAL | Strong cutaway | Helsinki selected-object identity cards | Kit live picking still needs stronger runtime/capture path |
| PERCEPTION/VSS | Deferred | Candidate-observation lane only | Needs licensed media/source detail and no-detection-truth guardrail |

## High-value ASK queries

1. `ask:london:wood_lane_source_context:q1` — What does CityBrain know about Wood Lane/Scrubbs Lane and which records support it?
2. `ask:nyc:mvc_cascade_context:q1` — What is known about MVC crash 4463710, candidate tax-lot context, and response-resource context?
3. `ask:barcelona:flow_context_explorer:q1` — What do Barcelona flow packs know by source family, geography, and limitation?
4. `ask:london:planning_identity_context:q1` — Address / UPRN / planning context from London identity and PLD outputs.
5. `ask:global:what_is_uncertain:q1` — What is uncertain or unsupported in this packet?
6. `ask:global:what_changed:q1` — What changed between snapshots? This is only partial until snapshot cadence is normalized.

## High-value WATCH queries

1. `watch:proximity_works_to_access@v1` — London access-context review candidates from works/disruptions near access assets.
2. `watch:incident_to_candidate_asset_context@v1` — NYC incident-to-candidate-asset/context review.
3. `watch:low_confidence_link_or_source_gap@v1` — cross-city quality/source-depth review queue.
4. `watch:visual_identity_missing_graph_link@v1` — visual identity/CER graph-link review once Kit/CER sidecars are normalized.

## Strong BRIEF opportunities

1. `brief:london:wood_lane_packet` — Situation, records, proximity-not-causality limitation, review options, and human stop.
2. `brief:nyc:mvc_cascade_packet` — MVC crash context, candidate asset/resource context, route/review itinerary limitations, and human stop.

## Strong CHECK opportunities

1. `check:global:claim_boundary_and_source_depth` — checks whether an answer/story/packet exceeds source and claim boundaries.
2. `check:singapore:source_resolution` — currently weak but useful as a readiness checker for Singapore/VSS/API access.

## What D9 should build next

Build a local/replay product-mode console with:
- Ask panel: cited answers with source cards and “known / unknown / cannot claim” sections.
- Watch panel: named-query manual review queue, not live monitoring.
- Brief panel: brief generator for London and NYC.
- Check panel: claim-boundary/source-depth checker available beside every answer/brief/queue item.
- Recall cutaway: Chicago memory cards only when match reasons and non-inference limits are visible.

## What D9 should not build yet

- No Diff product mode beyond a deferred/cadence note.
- No Perception/VSS implementation.
- No production/public API.
- No autonomous monitoring or alerts.
- No dispatch/routing/control/enforcement.
- No official ticket/case creation.
- No legal/certified finding.
- No automated action.

## Recommended implementation task

`MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-RUNTIME-R1`
