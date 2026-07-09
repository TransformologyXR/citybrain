# ENTRY PROMPT — CityBrain D8 Source-Record UI Integration

Run the following sequence in order. Do not skip failed gates. Do not fabricate source records. Do not let internal CityBrain fixture IDs appear in the default UI.

1. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-INTEGRATION-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-INTEGRATED-SOURCE-RECORD-BUNDLE-ADAPTER-R1`
3. `MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-CARDS-R2`
4. `MAIN-CITYBRAIN-D8-MOMENT-SOURCE-RECORD-PARITY-R3`
5. `MAIN-CITYBRAIN-D8-CITY-FACT-DOM-ASSERTION-SMOKE-R4`
6. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CLOSEOUT`
7. `MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-MILESTONE-FREEZE`

Goal: the web UI defaults to actual city/source-derived records:
- London mobility records for situation/access context.
- Chicago case records for M02 similar-case memory.
- Helsinki semantic building records for M10/visual entity pick.
- Data-depth blockers for M13/M07/M08 if source records remain unavailable.

Success is not “nice wording.” Success is DOM-visible city facts from source bundles.
