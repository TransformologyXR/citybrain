# MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-RENDERING-PATCH-R3

Patch apps/web-control-room so the default UI reads source_record_bundle.json / source_record_cards.json and renders city-source records, not CityBrain fixture labels.

Default UI rules:
- Default card titles must not be `Hero...`, `Observation 001`, `Similar case 001`, raw packet IDs, or enum names unless the card is explicitly a DATA DEPTH BLOCKER.
- Render source dataset/city/external id/place/time/summary/limitation visibly.
- Keep raw CityBrain refs under collapsed technical details.
- If data is missing, show DATA DEPTH BLOCKER with missing fields.

Required output:
- WEB_SOURCE_RECORD_RENDERING_PATCH_DECISION.json
- WEB_SOURCE_RECORD_RENDER_MAP.json
- UPDATED_DOM_CAPTURE.html
- NO_GENERIC_FIXTURE_LABEL_AUDIT.json
