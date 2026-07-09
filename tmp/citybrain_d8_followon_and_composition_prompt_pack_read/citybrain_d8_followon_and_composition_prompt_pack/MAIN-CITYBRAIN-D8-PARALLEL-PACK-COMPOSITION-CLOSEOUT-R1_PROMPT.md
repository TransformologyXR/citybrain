# TASK: MAIN-CITYBRAIN-D8-PARALLEL-PACK-COMPOSITION-CLOSEOUT-R1

## Purpose
Formally close the D8 parallel prompt pack by composing all D8 lanes into one decision-grade handoff, scoreboard, and claim-boundary register. This task is documentation/composition/verification only; it should not add new source downloads or feature builds.

## Context
The D8 parallel prompt pack previously closed as:
`PASS_CITYBRAIN_D8_PARALLEL_PROMPT_PACK_WITH_LIMITATIONS`

Known lane results:
- Mobility abstain patch: M04/M05 explicit abstain semantics.
- VSS acquisition/readiness: package exists, but real VSS gates remain closed.
- Web+Kit smoke: local web bundle consumed, 12 moments checked, Kit handoff validated only.
- Helsinki: sidecar smoke/USDA handoff; later manual alignment R2 may exist.
- Chicago: bounded city-remembers sample; later reviewed matching R2 may exist.

This closeout should include the three R2 follow-ons if present:
- MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2
- HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2
- CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2

## Inputs
Use existing outputs if present:
- outputs/citybrain_d8_parallel_prompt_pack_closeout/
- outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/
- outputs/main_citybrain_d8_vss_licensed_corpus_acquisition_r1/
- outputs/main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/
- outputs/main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/
- outputs/d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/
- outputs/helsinki_kit_object_pick_manual_alignment_r2/
- outputs/chicago_similar_case_bounded_enrichment_r1/
- outputs/chicago_similar_case_reviewed_matching_r2/
- all relevant decision JSONs, scoreboards, manifests, limitations, and audit files

## Hard boundaries
- Do not mutate prior outputs.
- Do not download new data.
- Do not repair individual lanes in this closeout; record their status honestly.
- Do not convert limitations into pass claims.
- Do not claim production, legal, certified, live, autonomous, VSS runtime, or full citywide twin readiness.

## Required work

### 1. Lane inventory
Inventory every D8 lane and follow-on with:
- task_id
- output_root
- status
- decision_file
- primary artifacts
- parse/hash/audit status
- demonstrability contribution
- limitations
- next recommended task

### 2. Demonstrability scoreboard
Create a D8 scoreboard with categories:
- demonstrable now
- demo-consumable with limitation label
- handoff-only
- acquisition/readiness-only
- explicitly gated/closed
- parked

At minimum classify:
- 12 Web+Kit moments
- M04/M05 abstain moments
- VSS sample/runtime gates
- Helsinki sidecar/manual alignment outputs
- Chicago city-remembers outputs

### 3. Claim-boundary register
Create a claim register with allowed and forbidden wording.

Must preserve:
- VSS gates closed unless R2 truly opened a sample-only gate
- visual mesh backdrop-only unless manual alignment evidence exists
- HSL bbox-limited mobility context
- Chicago bounded-sample-only memory
- M04/M05 abstain semantics
- no production/live/legal/certified/autonomous claims

### 4. Handoff decision
Produce one closeout decision that states:
- what D8 has proven
- what D8 has not proven
- what is safe to demo
- what requires human/manual review
- what remains blocked by data/source/runtime gaps
- recommended next task: demonstrable surface integration R1, unless blockers make it premature

### 5. Artifact nav map
Create a machine-readable map of artifact paths for downstream demo integration.

## Required outputs
Create output root:
`outputs/main_citybrain_d8_parallel_pack_composition_closeout_r1/`

Required files:
- `MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_DECISION.json`
- `D8_LANE_INVENTORY.json`
- `D8_DEMONSTRABILITY_SCOREBOARD.json`
- `D8_CLAIM_BOUNDARY_REGISTER.md`
- `D8_ALLOWED_AND_FORBIDDEN_WORDING.json`
- `D8_ARTIFACT_NAV_MAP.json`
- `D8_CLOSEOUT_HANDOFF.md`
- `D8_NEXT_TASK_RECOMMENDATION.md`
- `HASH_MANIFEST.sha256`
- `RUN_AUDIT.json`

## Audits
Must run and record:
- JSON parse audit
- referenced-artifact existence audit
- no prior output mutation audit
- secret scan
- claim boundary audit
- limitation preservation audit
- hash manifest verification

## Acceptance criteria
Pass with limitations if:
- all available D8 lanes are inventoried
- scoreboard separates demonstrable, handoff-only, readiness-only, and gated outputs
- claim boundaries are explicit
- no limitation is silently upgraded into a stronger claim
- next demo-surface integration task has a clean artifact map to consume
- all audits pass

Expected final status:
`PASS_MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_WITH_LIMITATIONS`
