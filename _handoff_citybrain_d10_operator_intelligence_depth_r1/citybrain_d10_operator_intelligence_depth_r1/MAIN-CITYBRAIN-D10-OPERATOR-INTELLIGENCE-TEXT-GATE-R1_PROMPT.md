# MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R1

## Purpose

Rerun the brutal operator-manual text gate after D10 product-depth changes.

## Product goal

The default visible text should read like a city operator manual/work board, not a platform implementation report.

## Required actions

1. Render/capture the default cockpit DOM after D10 changes.
2. Export only default human-visible text to:
   `outputs/main_citybrain_d10_operator_intelligence_text_gate_r1/DEFAULT_VISIBLE_TEXT.txt`
3. Check for hard-fail visible terms outside inspector/details:
   - `ask:`
   - `watch:`
   - `@v1`, `@v2`
   - `Ranker`
   - `Recency input`
   - `Evidence input`
   - `Uncertainty class`
   - `Review verb`
   - `runtime bundle`
   - `product mode`
   - `packages/fixtures`
   - `outputs/`
   - `PASS_`, `PARTIAL_`, `DEFERRED_`
   - `data-mode-run-id`
4. Check for required operator phrases or equivalents:
   - why this needs review
   - why this is ranked here
   - records on file
   - what may be nothing
   - suggested human check
   - what this does not prove
   - no official case or action was created
5. Check grammar/copy quality for top obvious defects.
6. Do not self-certify final pass. Mark ready for ChatGPT/manual validation.

## Output

Write:

1. `outputs/main_citybrain_d10_operator_intelligence_text_gate_r1/DEFAULT_VISIBLE_TEXT.txt`
2. `outputs/main_citybrain_d10_operator_intelligence_text_gate_r1/OPERATOR_INTELLIGENCE_TEXT_GATE_REPORT.json`
3. `outputs/main_citybrain_d10_operator_intelligence_text_gate_r1/OPERATOR_INTELLIGENCE_TEXT_GATE_DOM_CAPTURE.html`

Minimum report schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R1",
  "status": "READY_FOR_CHATGPT_MANUAL_VALIDATION" ,
  "self_certified_final_pass": false,
  "hard_fail_term_hits": {},
  "required_operator_phrase_hits": {},
  "visible_text_path": "...",
  "dom_capture_path": "...",
  "copy_limitations": []
}
```

## Fail locally if

- Any hard-fail term appears in default visible text.
- The text reads primarily as product architecture/platform debug.
- Action/alert/live-monitoring claims appear.
