# Implementation Notes R22

Recommended implementation path:

1. Use R21 output root or ZIP as input.
2. Validate `R21_CLOSEOUT_DECISION.json` status.
3. Load review tile/cards/fixture JSON.
4. Emit a normalized `HUMAN_REVIEW_SURFACE_PACKET_R22.json`.
5. If the app has a local preview route, write a simple fixture file to the expected public/data path and request that route.
6. If no app route exists, create `COCKPIT_SURFACE_RENDER_FIXTURE_R22.json` with layout sections:
   - header
   - evidence summary
   - frame cards
   - false-positive/missed-annotation summaries
   - source-class labels
   - boundary labels
   - limitations
7. Do not package image/media files.
8. Hash only packaged files.
