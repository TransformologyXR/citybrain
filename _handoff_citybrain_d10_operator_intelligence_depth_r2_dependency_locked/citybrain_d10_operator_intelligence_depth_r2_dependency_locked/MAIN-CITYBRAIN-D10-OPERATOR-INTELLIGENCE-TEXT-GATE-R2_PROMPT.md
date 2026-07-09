# MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R2

## Purpose
Repeat the operator-manual text gate after D10 intelligence changes.

## Method
- Render/export default visible text.
- Judge hard-fail tokens and product-vs-city language.
- Technical tokens may appear only in inspector/details/DOM attributes, not in default operator text.
- Preserve source/citation readability.

## Hard fail terms in default visible text
- ask:
- watch:
- @v1 / @v2
- Ranker
- Recency input
- Evidence input
- Uncertainty class
- Review verb
- runtime bundle
- product mode
- packages/fixtures
- outputs/
- PASS_ / PARTIAL_ / DEFERRED_
- data-mode-run-id
- source graph / planning identity graph / implementation terms

## Required operator phrases
- Why this needs review
- Why this is ranked here
- Records on file
- What may be nothing
- Suggested human check
- What this does not prove
- No official case or action was created

## Output
`OPERATOR_INTELLIGENCE_TEXT_GATE_R2_REPORT.json`
and `DEFAULT_VISIBLE_TEXT_R2.txt`

Do not self-certify final product pass if ChatGPT/manual validation is requested later.
