# CityBrain D10 Operator Intelligence Depth R2 — Dependency-Locked Shared Context

Status: supersedes `citybrain_d10_operator_intelligence_depth_r1.zip`.

This package implements the amended D10 plan after the roadmap correction:
D10 should deepen operator intelligence, start the DIFF snapshot clock, and probe Kit environment readiness now.
It must not spend work on external validation/capture loops.

## Plan of record: D10–D14

1. **D10 — Operator Intelligence Depth**
   - Deeper deterministic search over retained city data.
   - Expanded WATCH query library.
   - Data-driven patch board.
   - Selected-item investigation content.
   - Field-computed RECALL reasons.
   - ASK/search/refusal smokes.
   - Start DIFF source-record snapshot cadence.
   - Run Kit/Omniverse runtime probe as a side-task.
   - Re-run D9 capability regression at closeout.

2. **D11 — Operator Workflow / Review Workspace**
   - Owns state/lifecycle, not content.
   - Local notes, hold, needs-source, abstain, mark reviewed, local session summary, export.
   - Must not mint official case/ticket IDs.
   - Exit includes a small task-based real-operator validation gate that produces the spontaneous question corpus.

3. **D12 — City Data Depth + Real DIFF**
   - Data must land with its consumer in the same sprint.
   - No dataset without a named WATCH query, ASK template, or RECALL matcher.
   - D10-started snapshot cadence should provide raw material.
   - Exit: limited record/entity-level DIFF if comparable snapshots exist.

4. **D13 — Spatial Twin / Omniverse One-Truth Cockpit**
   - Conditional on D10 Kit probe.
   - Web selected item and Kit selected object must resolve to same evidence packet, same limits, and same no-action state.

5. **D14 — Governed Open ASK + Production Readiness Track**
   - Requires D11 external operator question corpus as a preflight input.
   - Router maps question -> template + args or refusal.
   - Router never answers directly.
   - Production readiness is a track, not a claim.

## Durable boundary

- Local/LAN/replay/review/query context only.
- Human review required.
- No autonomous action.
- No dispatch.
- No alerting as operational command.
- No routing/control/enforcement.
- No official ticket/case creation.
- No legal/certified finding.
- No production/public API claim.
- No live-monitoring claim unless explicitly proven later.
- No identity/biometric inference.
- No model-generated factual claim without retained source evidence.
- Track D / human authority remains after any future promotion.
- `execution_state` remains not_executed.

## Important corrections locked in this R2 package

### Validation is a gate, not a sprint
Do not run external validation in D10. Do not create another capture loop. But D11 exit must include a small set of real operator task sessions whose deliverable is the spontaneous question corpus. D14 cannot start Open ASK implementation without that corpus.

### DIFF clock starts in D10
D10 must start source-record snapshot cadence and write a cadence ledger. Do not claim live DIFF. D12 needs comparable snapshots; elapsed time cannot be compressed later.

### Kit runtime probe runs in D10
D10 must probe whether Omniverse Kit/Composer can load the CityBrain extension/environment on the target 4070 stack. Do not build D13 now. The probe result decides whether D13 holds its roadmap slot or becomes an environment-repair sprint.

### D12 consumption rule
No dataset lands without its consuming product mode in the same sprint: WATCH query, ASK template, or RECALL matcher. This prevents a return to validated record walls.

### D10/D11 seam
D10 owns selected-item investigation **content**:
linked entities, source records, precedent matches, missing evidence, bounded questions, answer/check/brief content.

D11 owns selected-item workflow **state**:
local notes, mark reviewed, hold, needs source, abstain, session summary, export.

### Standing regression gate
D9 capability regression must rerun at every closeout D10–D13:
held-out ASK, out-of-scope refusal, non-story BRIEF, mode-run stamping, no-action boundary.
