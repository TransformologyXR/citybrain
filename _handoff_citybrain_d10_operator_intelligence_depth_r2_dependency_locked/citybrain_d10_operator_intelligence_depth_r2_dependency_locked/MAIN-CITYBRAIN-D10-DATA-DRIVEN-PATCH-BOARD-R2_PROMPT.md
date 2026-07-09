# MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R2

## Purpose
Make the patch board more data-driven using the expanded query library and deterministic search outputs.

## Requirements
- Keep default surface operator-readable.
- No implementation tokens in visible text.
- Preserve mode-run/data attributes for traceability.
- Queue items must be city/operator review items.
- Data-quality items can appear only if tied to a selected city situation or in CHECK.
- Rank must remain deterministic.
- Every item needs:
  - human title
  - place/scope
  - record time/as-of date
  - why this needs review
  - why ranked here
  - records on file
  - what may be nothing
  - suggested human check
  - known/unknown/cannot-claim path into selected item

## Output
`DATA_DRIVEN_PATCH_BOARD_R2.json`
and updated cockpit DOM/HTML artifacts if applicable.

## Hard fail
A board that validates but reads like source inventory fails.
