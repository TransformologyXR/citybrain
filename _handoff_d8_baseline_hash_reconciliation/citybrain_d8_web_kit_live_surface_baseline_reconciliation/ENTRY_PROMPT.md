You are continuing CityBrain after `PASS_MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_MILESTONE_FREEZE_WITH_LIMITATIONS`.

A direct validation of the uploaded Web+Kit live-surface ZIP found the milestone decision green, web live launch green, DOM certified-value assertions green, moment parity green, one-truth drift green, forbidden command rejection green, and Kit runtime correctly marked unavailable. However, nested validation-package hash verification found source-baseline mismatches for bridge runtime artifacts such as `packages/fixtures/mobility_access/bridge/audit/bridge_audit.jsonl` and bridge `outbox/*.event.json` files across earlier stage manifests.

Task:
Run a lightweight baseline reconciliation before external capture/viewer validation.

Required task:
`MAIN-CITYBRAIN-D8-WEB-KIT-LIVE-SURFACE-BASELINE-HASH-RECONCILIATION`

Goals:
1. Inspect the latest Web+Kit live-surface milestone freeze output and validation package.
2. Confirm final decision remains PASS with limitations.
3. Recompute hashes for maintained source roots and runtime bundle roots as of the final freeze baseline.
4. Classify files into:
   - immutable maintained source baseline
   - certified runtime bundle baseline
   - volatile bridge runtime artifacts
   - output/audit artifacts
5. Explain any hash mismatches found in prior stage manifests.
6. Do not alter certified upstream outputs.
7. Do not alter runtime bundle truth to make UI pass.
8. Produce a clean baseline hash manifest for the final source/runtime snapshot.
9. Produce a volatile-file ledger so future validators do not treat append/outbox artifacts as immutable source drift.
10. Preserve all boundaries.

Expected output root:
`outputs/main_citybrain_d8_web_kit_live_surface_baseline_hash_reconciliation/`

Expected artifacts:
- `MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `SOURCE_BASELINE_HASH_MANIFEST.json`
- `RUNTIME_BUNDLE_BASELINE_HASH_MANIFEST.json`
- `VOLATILE_BRIDGE_ARTIFACT_LEDGER.json`
- `PRIOR_STAGE_HASH_MISMATCH_EXPLANATION.md`
- `VALIDATION_RECONCILIATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Pass only if:
- Final live-surface milestone is discovered and green.
- Web live evidence remains PASS.
- Moment parity remains PASS.
- Kit unavailable status is preserved honestly if still unavailable.
- All maintained source files at final baseline hash cleanly.
- Runtime bundle hashes cleanly.
- Volatile bridge files are explicitly classified and not silently ignored.
- No upstream certified artifacts are mutated.
- No production/public API/auth/RBAC/live monitoring/action claims are introduced.

Expected status:
`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_WITH_LIMITATIONS`

Recommended next task after pass:
`MAIN-CITYBRAIN-D8-POST-HANDOFF-EXTERNAL-CAPTURE-FRONTEND-FOLLOW-THROUGH`
