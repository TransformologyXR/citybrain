# ENTRY PROMPT — CITYBRAIN D8 R3 FOLLOW-ON CODEX HANDOVER

You are operating in the CityBrain repository.

Run the three D8 R3 follow-on tasks in this handover pack, preserving all D8 boundaries and claim limitations.

## Task list

1. `HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3`
2. `CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3`
3. `MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3`

## Current upstream state to assume

D8 follow-on/composition pack passed with limitations.

Known upstream outputs:
- `outputs/citybrain_d8_followon_and_composition_prompt_pack_closeout/`
- `outputs/helsinki_kit_object_pick_manual_alignment_r2/` or equivalent R2 Helsinki output root
- `outputs/chicago_similar_case_reviewed_matching_r2/` or equivalent R2 Chicago output root
- `outputs/main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/` or equivalent VSS R2 output root
- `outputs/main_citybrain_d8_demonstrable_surface_integration_r1/`
- `outputs/main_citybrain_d8_parallel_pack_composition_closeout_r1/`

If exact root names differ, discover them from closeout/decision JSONs. Do not invent upstream evidence.

## Non-negotiable boundaries

- Do not mutate prior certified outputs.
- Do not start large downloads.
- Do not scrape or ingest external media unless it is already present locally and explicitly licensed for this project.
- Do not claim production, legal, certified, live, autonomous, enforcement, dispatch, or command/control capability.
- Do not claim VSS runtime readiness unless every VSS sample-ingest acceptance criterion is satisfied.
- Treat Helsinki USD/USDA outputs as sidecar/review overlays unless manual review evidence proves object-level alignment.
- Treat Chicago similar-case matching as bounded demo memory, not citywide operational memory.

## Required per-task audit pattern

Each task should emit:
- Decision JSON
- README / handoff note
- JSON parse audit
- Secret scan audit
- Claim-boundary audit
- No-prior-output-mutation audit
- Referenced-artifact existence audit
- Hash manifest generated last

## Pack-level closeout

After running all three tasks, create:

`outputs/citybrain_d8_r3_followon_prompt_pack_closeout/CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_CLOSEOUT.json`

It should summarize:
- status per task
- key artifacts
- demo-surface improvements
- still-closed gates
- limitations
- audit results
- recommended next task

Expected final status:
`PASS_CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_WITH_LIMITATIONS`

Use `FAIL` only for hard parsing/IO/corruption errors that make outputs untrustworthy.
