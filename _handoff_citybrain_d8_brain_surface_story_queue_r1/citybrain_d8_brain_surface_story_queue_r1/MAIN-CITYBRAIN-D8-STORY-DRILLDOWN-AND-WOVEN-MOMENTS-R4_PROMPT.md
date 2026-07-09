# MAIN-CITYBRAIN-D8-STORY-DRILLDOWN-AND-WOVEN-MOMENTS-R4

Implement story drilldown panels for each primary story.

Each drilldown must show:
1. What happened / review premise
2. Source records
3. What CityBrain connected
4. What is uncertain
5. Review-only choices
6. Where it stops / human review boundary
7. Cutaways/trust moments available

Woven moments:
- M07 refusal: only if refusal/review log exists; otherwise show a data-depth note in the story, not a fake refusal.
- M08 human stop: render from scenario layer human_stop fields.
- M12 limitations: one story-level limitations section, not repeated per card.
- Chicago precedent: render as "recall a precedent" only where match reason is specific; otherwise parked.
- Helsinki visual pick: render as "show visual identity cutaway" only as a capability, not as primary story.

Produce:
- `STORY_DRILLDOWN_RENDER_MAP.json`
- `WOVEN_MOMENT_RENDER_REPORT.json`
- `MISSING_MOMENT_DATA_DEPTH_LEDGER.json`
