# MAIN-CITYBRAIN-D8-HELSINKI-SEMANTIC-TWIN-VISUAL-ENTITY-PICK-PREFLIGHT

Goal: preflight Helsinki as source-backed visual object -> graph entity showcase.

Candidate official sources:
- Helsinki 3D semantic city information model.
- Helsinki WFS/CityGML/CityJSON building data.
- Kalasatama CityGML ZIP if small enough.
- Reality mesh only as visual backdrop, not identity truth.

Tasks:
1. Probe WFS/CityGML access.
2. Confirm license/attribution.
3. Define bounded sample: 100-2,000 buildings or Kalasatama-only.
4. Required fields: GMLID or equivalent, RATU, VTJ_PRT if present, measuredHeight, usage, yearOfConstruction, roofType, geometry/LoD.
5. Write preflight report.

PASS only if semantic building records can be sampled with building identifiers.
