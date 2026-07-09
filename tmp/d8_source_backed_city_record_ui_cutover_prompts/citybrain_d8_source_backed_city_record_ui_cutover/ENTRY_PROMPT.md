# ENTRY — CityBrain D8 Source-Backed City Record UI Cutover

Run this sequence only after the Actual-Record-Grounded UI still renders CityBrain fixture records instead of official city-source records.

Goal: stop UI copy/panel polishing and cut over the web control-room default view to render actual city data records (official source rows, source-derived IDs, places, timestamps, and evidence fields), or fail honestly if the certified Mobility Access bundle has no such records.

Sequence:
1. MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CUTOVER-PREFLIGHT
2. MAIN-CITYBRAIN-D8-CERTIFIED-RUNTIME-TO-CITY-SOURCE-RECORD-AUDIT-R1
3. MAIN-CITYBRAIN-D8-SOURCE-RECORD-BUNDLE-BUILD-R2
4. MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-RENDERING-PATCH-R3
5. MAIN-CITYBRAIN-D8-DOM-SOURCE-RECORD-ASSERTION-SMOKE-R4
6. MAIN-CITYBRAIN-D8-SOURCE-BACKED-UI-CLOSEOUT
7. MAIN-CITYBRAIN-D8-SOURCE-BACKED-UI-MILESTONE-FREEZE

Hard rule: CityBrain-generated fixture IDs such as `hero-*`, `HERO-*`, `inv_option_*`, `d7_candidate_observation:*`, `similar_case:*`, `cascade_attachment:*`, and internal stage names do not count as official city records in the default UI. They may appear only under closed technical details or as provenance/trace references.

Default UI must show official/source-derived city records, or visible DATA DEPTH BLOCKER cards. Do not fill missing city records with nicer prose.
