# MAIN-CITYBRAIN-D8-LONDON-MOBILITY-SOURCE-RECORD-PACK-PREFLIGHT

Goal: preflight a bounded London source-record pack for the Mobility Access corridor UI.

Why London:
The current scenario ref is `hero-lon-corridor`; if a London mobility/access source-record pack can be built, it is the shortest path from fixture labels to real city data.

Candidate official sources:
- TfL Unified API road disruptions / roads endpoints.
- London Fire Brigade incident records as emergency/service context.
- London Air Quality Network API as environmental context if a mobility/environment cut is useful.

Tasks:
1. Discover current local data already present for London/TfL/LFB/LAQN before downloading.
2. Define a bounded geography/time/window for a mobility corridor pack.
3. Probe access without large pulls.
4. Write:
   - LONDON_MOBILITY_SOURCE_PREFLIGHT_DECISION.json
   - LONDON_SOURCE_ACCESS_STATUS.json
   - LONDON_LICENSE_AND_ATTRIBUTION_LEDGER.json
   - LONDON_RECORD_FIELD_MAP.md
   - LONDON_BLOCKERS_AND_LIMITATIONS.md

PASS only if at least one official/source-derived London dataset is accessible for bounded source-record extraction.
PARTIAL if APIs require credentials, sources are missing, or source fields do not support viewer-ready records.
