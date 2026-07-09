# MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT

## Purpose

Establish a clean preflight for D10 product-substance work. Preserve D9 cockpit state, operator-manual text gate result, and hard boundaries. Explicitly stop external validation/capture as the active lane.

## Inputs to inspect

- D9 operator cockpit UX outputs and freeze decision.
- D9 operator manual text gate outputs:
  - `DEFAULT_VISIBLE_TEXT.txt`
  - `OPERATOR_MANUAL_TEXT_GATE_REPORT.json`
  - DOM capture HTML
- D9 runtime/product mode bundle and overlay.
- Current web-control-room source.
- Available source cartridges/fixtures under `packages/fixtures/**` and relevant `outputs/**` with source records.

## Required actions

1. Locate and record the current D9 operator cockpit baseline.
2. Verify the operator text gate result is available and no hard-fail terms are present.
3. Verify the no-action boundary and `data-mode-run-id` traceability survived.
4. Record that external operator validation/capture is intentionally paused.
5. Record that Open ASK router remains contract-only and must not be implemented in this lane.
6. Record the authorized scope of D10:
   - deterministic search templates
   - WATCH query library expansion
   - data-driven patch board
   - selected-item investigation
   - field-computed RECALL match reasons
   - DIFF cadence/status only
   - operator text gate rerun

## Output

Write:

`outputs/main_citybrain_d10_operator_intelligence_depth_preflight/D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_DECISION.json`

Minimum fields:

```json
{
  "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT",
  "status": "PASS_D10_PREFLIGHT" or "FAIL_D10_PREFLIGHT",
  "d9_cockpit_baseline_found": true,
  "operator_manual_text_gate_found": true,
  "external_validation_paused": true,
  "open_ask_router_contract_only": true,
  "no_action_boundary_preserved": true,
  "blocking_gaps": [],
  "allowed_scope": []
}
```

## Fail if

- The current cockpit baseline cannot be found.
- The operator-manual text gate output cannot be found.
- The run plans to implement a model/Open ASK router.
- Any action/alert/dispatch/control claim is introduced.
