# Checklist

- [ ] Classify every default UI card as OFFICIAL_CITY_SOURCE_RECORD, SOURCE_DERIVED_CITY_RECORD, CITYBRAIN_FIXTURE_RECORD, or DATA_DEPTH_BLOCKER.
- [ ] Default UI contains zero CityBrain-only fixture cards pretending to be city facts.
- [ ] At least one real place/entity card displays a source-derived place/road/building identifier beyond `Hero...`.
- [ ] At least one evidence/case card displays a city, dataset/source, external/source record id, summary, and limitation.
- [ ] Observations/similar cases/cascades remain DATA DEPTH BLOCKER if only refs/counts exist.
- [ ] DOM smoke asserts the visible page contains real source labels and rejects Hero-only labels as default content.
- [ ] Technical details may contain raw IDs, collapsed by default.
- [ ] No facts invented; gaps are explicit.
