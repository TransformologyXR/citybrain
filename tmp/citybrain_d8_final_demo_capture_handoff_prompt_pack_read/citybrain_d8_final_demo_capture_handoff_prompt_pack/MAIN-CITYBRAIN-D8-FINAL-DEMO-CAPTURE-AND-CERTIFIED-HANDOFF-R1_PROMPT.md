# MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1

## Goal

Freeze CityBrain D8 as a shareable, reproducible, bounded local demo-state handoff.

This task should compose the accepted D8 lanes into one final review package:

- D8 demonstrable surface integration
- D8 follow-on/composition pack
- R3 follow-on pack
- Mobility M04/M05 abstain semantics
- Web+Kit local demo bundle
- Helsinki semantic USD/CER sidecar and manual object-pick review state
- Chicago bounded “city remembers” sample and demo query smoke
- VSS readiness/acquisition/sample-ingest gates, explicitly still closed

This is a final capture and certified-state handoff task, not a new data landing, not a feature expansion, not a productionization task, and not a VSS runtime task.

## Required task name

`MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1`

## Required output root

Create a new output root:

`outputs/main_citybrain_d8_final_demo_capture_and_certified_handoff_r1`

Do not write into or modify any prior output root except for normal read-only inspection.

## Upstream roots to inspect

Use these if present:

- `outputs/main_citybrain_d8_demonstrable_surface_integration_r1`
- `outputs/citybrain_d8_followon_and_composition_prompt_pack_closeout`
- `outputs/citybrain_d8_r3_followon_prompt_pack_closeout`
- `outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1`
- `outputs/main_citybrain_d8_web_kit_bundle_consumption_smoke_r1`
- `outputs/helsinki_kit_object_pick_manual_alignment_r2`
- `outputs/helsinki_kit_object_pick_manual_review_capture_r3`
- `outputs/chicago_similar_case_reviewed_matching_r2`
- `outputs/chicago_similar_case_demo_query_smoke_r3`
- `outputs/main_citybrain_d8_vss_licensed_corpus_acquisition_r1`
- `outputs/main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2`
- `outputs/main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1`
- `outputs/d4_helsinki_kalasatama_context_data_landing_r1`
- `outputs/citybrain_d8_parallel_prompt_pack_closeout`
- `outputs/data_gap_ledger_and_priority_matrix`

If any upstream root is missing, do not fail automatically. Record it in a missing-upstream register and continue if the final handoff can still be produced from available accepted roots.

## Required final status semantics

The expected status is:

`PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS`

Use `FAIL` only if critical decision files cannot be read, JSON parse fails in required final outputs, or audit boundaries cannot be preserved.

## Required outputs

### 1. Final decision JSON

Write:

`MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_DECISION.json`

Minimum fields:

- `task`
- `status`
- `run_timestamp_utc`
- `repo_root`
- `upstream_roots_checked`
- `missing_upstream_roots`
- `final_d8_summary`
- `lane_results`
- `demonstrable_surface`
- `demo_route`
- `certified_state`
- `still_closed_gates`
- `claim_boundaries`
- `audit_results`
- `recommended_next_tasks`

### 2. Final D8 scoreboard

Write:

`D8_FINAL_DEMO_SCOREBOARD.json`

Include one row/object per lane:

- mobility abstain patch
- VSS R1 acquisition
- VSS R2 sample acquisition
- VSS R3 sample ingest smoke
- Web+Kit smoke
- Helsinki data landing
- Helsinki context consumption
- Helsinki sidecar alignment smoke
- Helsinki object-pick review capture
- Chicago bounded enrichment
- Chicago reviewed matching
- Chicago demo query smoke
- D8 demonstrable surface integration
- D8 composition closeout

For each lane include:

- `status`
- `output_root`
- `decision_file`
- `demo_consumable`
- `claim_level`
- `limitations`
- `closed_gates`
- `evidence_refs`

### 3. Final 7-step demo route capture

Write:

`D8_FINAL_DEMO_ROUTE.md`

Use the 7-step local demo route from `D8_DEMO_INDEX.html` / demonstrable surface integration if present.

The route must explicitly cover:

1. Open local D8 demo index.
2. Show the D8 lane scoreboard / limitation labels.
3. Show the mobility M04/M05 abstain state.
4. Show Web+Kit bundle consumption result and 12 checked moments.
5. Show Helsinki sidecar/object-pick demo state, with `pending_review` label preserved.
6. Show Chicago bounded similar-case demo cards/query results, including the clean abstain for citywide/general trend.
7. Show VSS closed-gate readiness state and explain why no runtime/readiness claim is made.

If the local HTML file exists, reference it by relative path and absolute local path if available from upstream metadata.

### 4. Operator script

Write:

`D8_OPERATOR_SCRIPT.md`

Provide a human-readable walkthrough for an operator/demo presenter.

The script must use claim-safe language:

- “bounded local demo”
- “sidecar candidate”
- “pending review”
- “abstain”
- “sample gate closed”
- “visual backdrop only”
- “no production/live/legal/autonomous/VSS readiness claim”

Avoid language such as:

- production ready
- live monitoring
- certified detection
- legal violation
- autonomous action
- VSS ready
- full object-level alignment
- citywide memory

### 5. Executive summary

Write:

`D8_EXECUTIVE_SUMMARY.md`

Summarize D8 in business/product terms:

- what is demonstrable now
- what remains gated
- why this is valuable
- what the next credible build branch should be

Keep it concise and claim-safe.

### 6. Certified-state handoff

Write:

`D8_CERTIFIED_STATE_HANDOFF.md`

This should be the main handoff artifact.

Include:

- final status
- lineage from scouts through D8 surface
- lane-by-lane results
- accepted demo-consumable surfaces
- limitation register
- still-closed gates
- no-mutation/no-secret/no-claim audit summary
- hash-manifest note
- next task recommendations

### 7. Artifact index

Write:

`D8_FINAL_ARTIFACT_INDEX.json`

For every important artifact referenced in the handoff, include:

- `artifact_name`
- `relative_path`
- `source_output_root`
- `artifact_type`
- `exists`
- `used_for`
- `claim_boundary`

### 8. Limitation register

Write:

`D8_FINAL_LIMITATION_REGISTER.json`

Must include at least:

- VSS sample gate closed
- VSS runtime readiness gate closed
- no audited licensed corpus ingested
- no camera metadata/oracle/license/privacy complete sample
- Helsinki object-pick packets remain pending review unless explicit evidence exists
- Helsinki 3D mesh remains visual backdrop only
- no full object-level alignment claim
- Chicago sample is bounded, not citywide memory
- Chicago general/citywide trend query abstains
- M04/M05 use abstain semantics
- Web+Kit is local/demo/handoff only
- no legal/certified/production/live/autonomous/enforcement/dispatch/control claim

### 9. Final claim boundary audit

Write:

`CLAIM_BOUNDARY_AUDIT.json`

Scan all newly generated final files for unsafe positive claims.

The audit should explicitly assert booleans for:

- `production_claim_made`
- `legal_or_certified_claim_made`
- `live_monitoring_claim_made`
- `autonomous_action_claim_made`
- `vss_runtime_readiness_claim_made`
- `full_object_level_alignment_claim_made`
- `citywide_memory_claim_made`

Expected: all false.

### 10. Referenced artifact existence audit

Write:

`REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json`

Confirm important upstream decision files, demo HTML, maps, JSONL packets, scoreboards, and handoff files exist.

Missing optional roots should be recorded but not treated as blockers unless they prevent final D8 capture.

### 11. JSON parse audit

Write:

`JSON_PARSE_AUDIT.json`

All newly generated JSON and JSONL under the final output root must parse cleanly.

### 12. Secret scan audit

Write:

`SECRET_SCAN_AUDIT.json`

Scan newly generated files for obvious secrets, API keys, tokens, credentials, private keys, and AccountKey-like patterns.

Expected: PASS.

### 13. No prior output mutation audit

Write:

`NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`

Record a before/after check where feasible, or at minimum assert that only the new final output root was written.

Expected: PASS.

### 14. Hash manifest

Write:

`HASH_MANIFEST.sha256`

Important: write this after all other output files are complete and after final audits are written.

Include every generated final handoff artifact.

### 15. Optional ZIP

If feasible, create:

`main_citybrain_d8_final_demo_capture_and_certified_handoff_r1.zip`

The ZIP should contain only the final output root artifacts, not raw upstream payloads.

## Acceptance criteria

The run passes if:

- final decision JSON exists and parses
- final status is `PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS`
- D8 final scoreboard exists
- 7-step demo route exists
- operator script exists
- executive summary exists
- certified-state handoff exists
- artifact index exists
- limitation register exists
- final audits pass
- hash manifest verifies cleanly
- no prior outputs are mutated
- unsupported claims are not made

## Required final wording

The handoff should include this exact or equivalent claim-safe summary:

“D8 proves a bounded local demonstrable CityBrain surface across mobility, Web+Kit, Helsinki semantic sidecar, Chicago bounded similar-case memory, and VSS-gated readiness. It preserves all limitation labels and does not claim production, legal, certified, live, autonomous, enforcement, dispatch/control, full object-level alignment, citywide memory, or VSS runtime readiness.”

## Recommended next tasks after this handoff

Include these as options, not as automatically started work:

1. `MAIN-CITYBRAIN-D9-DEMO-POLISH-AND-REVIEW-LOOP-R1`
2. `HELSINKI-KIT-OBJECT-PICK-HUMAN-REVIEW-EVIDENCE-R4`
3. `CHICAGO-SIMILAR-CASE-BOUNDED-MEMORY-EXPANSION-R4`
4. `MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-TRUE-SAMPLE-ACQUISITION-R4`
5. `MAIN-CITYBRAIN-D9-DOMAIN-PACK-AND-CER-SEG-COMPOSITION-PREFLIGHT-R1`

## Hard boundaries

Do not:

- download new large data
- scrape or fabricate media
- ingest unlicensed VSS/video samples
- mutate prior certified output roots
- create production/live/legal/autonomous/VSS readiness claims
- convert `pending_review` to reviewed without explicit evidence
- convert visual backdrop into object-level identity without explicit evidence
- expand Chicago sample into citywide memory
- treat abstain moments as fully demonstrable positive moments
