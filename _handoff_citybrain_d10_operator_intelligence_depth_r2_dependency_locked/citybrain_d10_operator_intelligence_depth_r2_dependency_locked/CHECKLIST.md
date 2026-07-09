# CHECKLIST — D10 Operator Intelligence Depth R2

## Required outputs

- `D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_R2_DECISION.json`
- `SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2.json`
- `CITY_DATA_SEARCH_CONTRACT_R2.json`
- `WATCH_QUERY_LIBRARY_EXPANSION_R2.json`
- `DATA_DRIVEN_PATCH_BOARD_R2.json`
- `SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json`
- `RECALL_FIELD_MATCH_REASONS_R2.json`
- `DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json`
- `KIT_RUNTIME_PROBE_R0_REPORT.json`
- `ASK_SEARCH_AND_REFUSAL_SMOKE_R2.json`
- `OPERATOR_INTELLIGENCE_TEXT_GATE_R2_REPORT.json`
- `D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json`
- `ROADMAP_DEPENDENCY_HANDOFF_R2.md`
- `D10_OPERATOR_INTELLIGENCE_DEPTH_CLOSEOUT_R2_DECISION.json`
- `D10_OPERATOR_INTELLIGENCE_DEPTH_MILESTONE_FREEZE_R2_DECISION.json`
- `HASH_MANIFEST.sha256`
- local open index / README

## Hard gates

- D10 improves operator intelligence, not just copy.
- DIFF snapshot cadence starts in D10 and is logged.
- Kit runtime probe runs in D10 and is logged.
- D12 consumption rule is recorded for next sprint.
- D11 external validation gate is recorded as D14 dependency.
- Selected-item content/state seam is recorded:
  - D10 = content.
  - D11 = state.
- D9 capability regression reruns at closeout:
  - held-out ASK
  - out-of-scope refusal
  - non-story BRIEF
  - mode-run stamping
  - no-action boundary

## Boundary gates

- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official case/ticket, legal/certified finding, or action.
- No production/public API claim.
- No Open ASK model/router implementation.
- No live DIFF claim.
- No perception/VSS claim.
- No Kit feature claim from probe only.
- No fabricated operator sessions/question corpus.
- No unsupported source/fact generation.
