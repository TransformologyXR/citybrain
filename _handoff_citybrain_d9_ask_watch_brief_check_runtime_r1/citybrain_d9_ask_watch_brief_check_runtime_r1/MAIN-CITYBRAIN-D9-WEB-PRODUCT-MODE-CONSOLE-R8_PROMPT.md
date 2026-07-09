# MAIN-CITYBRAIN-D9-WEB-PRODUCT-MODE-CONSOLE-R8

Patch the web control room into a product-mode console.

## Default surface

Open on:
- Ask
- Watch
- Brief
- Check

Story queue may remain, but it is no longer the whole product.

## UI requirements

### Ask
- input/sample question list
- cited answer view
- knowns/unknowns/cannot-claim
- sources and limitations

### Watch
- named-query queue
- manual-review badges
- false-positive notes
- not live monitoring label

### Brief
- generate/open London and NYC briefs
- source/evidence/option/limitation sections

### Check
- run check on answer/brief/queue item
- PASS/PARTIAL/BLOCKED with reasons

### Recall cutaway
- optional side panel only

## Hard gate

The UI must not become a record gallery or story-only viewer.

## Required artifacts

- patched web source
- `D9_WEB_PRODUCT_MODE_DOM_ASSERTION_REPORT.json`
- `D9_WEB_PRODUCT_MODE_SCREENSHOT_OR_DOM_CAPTURE.html`
- `D9_WEB_PRODUCT_MODE_CONSOLE_R8_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_WEB_PRODUCT_MODE_CONSOLE_R8_WITH_LIMITATIONS`
