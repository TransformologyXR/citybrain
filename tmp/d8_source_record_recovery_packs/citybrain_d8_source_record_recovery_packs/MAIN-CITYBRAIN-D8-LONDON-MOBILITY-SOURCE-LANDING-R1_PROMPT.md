# MAIN-CITYBRAIN-D8-LONDON-MOBILITY-SOURCE-LANDING-R1

Goal: land a small bounded London source sample, not a full download.

Required:
- Use source URLs/endpoints recorded in preflight.
- Prefer 10-100 records per source, bounded by time/geography/query.
- Preserve raw responses under a source landing root.
- Do not mutate certified D8 or Mobility Access runtime bundle.

Suggested records:
- Road disruption/event/planned works records with road/street name, description, timestamps, severity/status if available.
- LFB incident records with incident number/date/location/type if already local or bounded download practical.
- LAQN station/measurement records only if useful and bounded.

Outputs:
- LONDON_MOBILITY_RAW_SOURCE_INDEX.json
- raw source files
- LONDON_SOURCE_LANDING_REPORT.json
- SECRET_AUDIT.json
- HASH_MANIFEST.json

PASS only if raw official/source-derived city records are landed and parseable.
