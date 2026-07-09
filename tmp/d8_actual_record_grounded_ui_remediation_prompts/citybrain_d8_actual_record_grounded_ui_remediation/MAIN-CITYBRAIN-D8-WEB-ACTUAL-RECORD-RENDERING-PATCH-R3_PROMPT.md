# MAIN-CITYBRAIN-D8-WEB-ACTUAL-RECORD-RENDERING-PATCH-R3

## Objective

Patch `apps/web-control-room` so the default demo view renders actual records and fact cards, not subsystem labels, counts, or generic CityBrain descriptions.

## Required UI changes

### Replace generic story text

Replace generic copy such as:

- "Mobility Access, D7, similar cases, cascade, trace, and Track D are shown together."
- "Cross-city memory provides 4 similar cases as context."
- "6 D7 candidate observations are visible as possible evidence."
- "Some links are qualitative and context-only."

with data-grounded cards generated from `RENDERABLE_RECORD_INVENTORY.json` and the runtime bundle.

### Default layout

Default visible sections should be:

1. **What happened** — actual corridor/place/scenario facts available in the bundle.
2. **What records are connected** — actual entity cards and relationship link cards.
3. **What was observed** — actual D7 observation cards.
4. **What past cases were similar** — actual similar-case cards.
5. **What is uncertain** — actual low-confidence/qualitative/context-only links.
6. **What a human can review** — option cards with actual axes/values/statuses.
7. **Where the system stops** — actual Track D packets and rejected command logs.
8. **Technical details** — raw IDs, counts, packet refs; collapsed by default.

### Missing data behavior

If actual record fields are missing, the UI must show a clear data-depth gap, not generic filler.

Example:

```text
This bundle contains 6 candidate observation IDs, but no human-readable observation summaries. Viewer-ready observation cards are blocked until the observation records include source, time, location, and candidate label.
```

## Required evidence

Produce local launch evidence again:

- `WEB_LOCAL_LAUNCH_EVIDENCE.json`
- `WEB_RENDERED_ACTUAL_RECORD_ASSERTION_REPORT.json`
- DOM scrape or screenshot proving an actual record title/ref appears in a default panel
- DOM scrape proving technical packet IDs are collapsed by default

## Output artifacts

- updated `apps/web-control-room` source
- `WEB_ACTUAL_RECORD_RENDERING_PATCH_REPORT.json`
- `WEB_RENDERED_ACTUAL_RECORD_ASSERTION_REPORT.json`
- `DATA_DEPTH_GAP_UI_REPORT.json`
- `HASH_MANIFEST.json`

