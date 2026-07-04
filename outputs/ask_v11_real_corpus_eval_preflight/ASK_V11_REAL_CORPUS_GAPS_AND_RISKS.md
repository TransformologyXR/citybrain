# ASK v1.1 Real Corpus Gaps And Risks

## Missing Real-Corpus Families

- `contradiction`: no retained pair with conflicting values was identified during this preflight. Keep sealed fixture coverage until a real retained contradiction pair is found or create an eval-only contradiction pair from retained records in R1.

## Families Only Partly Covered By Real Corpus

- `renderer_no_undowngrade`: real Wood Lane evidence exists, but the unsafe render proposal is an eval-harness injection.
- `unsupported_template_gap`: the gap behavior is a router/compiler behavior more than a corpus fact; D9 unsupported-question material can anchor it.
- `raw_query_boundary`: retained operator session template can anchor it, but the raw_query injection remains an eval-harness safety probe.
- `no_data`: requires a negative lookup adapter against retained artifacts.

## Real Sources Available But Not Yet Mapped To ASK Templates

- London EV source row 87 and related rapid charging cards need mapping to `entity_profile` and `selected_item_followup`.
- Wood Lane story and source records need mapping to `subject_answer`, `source_record_profile`, and `patch_queue_query`.
- NYC MVC cascade story needs mapping to `subject_answer` and candidate/inferred-link checks.
- Guardrail refusal records can anchor boundary-action cases, but they should not become normal evidence execution.
- Human review stop records can support no-action boundary checks.

## Current Fixture-Only G5 Blockers

- G5 executes only the sealed fixture source set in `packages/ask_v11/fixtures.py`.
- Real retained artifact refs like `TIMS-219173`, `infrastructure_context_asset:uk-london:ev_charging_site:87`, and `story:nyc:cascade:mvc_crash_4463710` are not runtime fixture aliases.
- R1 should not change G5. It should add an eval-only corpus adapter that produces eval evidence inputs or expected observations outside G1-G8 runtime.

## Non-Runtime Eval Adapter Need

R1 should include a corpus reader/adapter that:

- reads retained JSON artifacts only,
- normalizes selected source records into eval case evidence,
- maps selected_item_ref and source_record_ref values to retained artifact rows,
- records no_data when rows are absent,
- emits expected CHECK/render assertions,
- never calls live endpoints,
- never mutates review or source artifacts.

## Live/Production Retrieval Risks

- Story artifacts include source URLs, but R1 must treat them as citations only.
- TfL records are described as active at probe time; R1 must treat them as retained replay evidence, not current live status.
- EV charging records do not carry live occupancy/fault/availability.

## Official Action And Legal/Certified Claim Risks

- Guardrail records mention blocked dispatch/approval/control requests; R1 must not treat those as executed actions.
- NYC cascade records include response-resource context; R1 must not render dispatch or routing claims.
- Helsinki visual entity records include semantic building IDs and candidate prim paths; R1 must not certify legal identity, property status, or physical geometry beyond retained source context.
- Chicago similar-case records must remain precedent/context only, not enforcement or prediction.

## Recommendation

Proceed to `ASK-V11-REAL-CORPUS-EVAL-R1` only as an eval harness package. Any runtime changes should wait until R1 reports concrete failure cases with Sev labels.
