# MAIN-CITYBRAIN-D8-HELSINKI-SEMANTIC-TWIN-PILOT-DATA-LANDING

Goal: bounded Helsinki semantic twin pilot for "picked visual object -> graph entity" demonstration.

Scope:
- Pull WFS metadata and a bounded sample of 500–2,000 semantic buildings if reachable.
- Download the small Kalasatama CityGML ZIP if reachable and within bounded size expectations.
- Optionally inspect one small visual mesh tile only if the source index and size are acceptable.
- Do not pull citywide 177GB mesh.

Produce:
- HELSINKI_SOURCE_INVENTORY.json
- HELSINKI_LICENSE_AND_ATTRIBUTION.md
- HELSINKI_SEMANTIC_BUILDING_SAMPLE.jsonl
- HELSINKI_CITYGML_SAMPLE_MANIFEST.json
- HELSINKI_USD_PRIM_METADATA_PLAN.md
- HELSINKI_ID_CROSSWALK_SCHEMA.json
- HELSINKI_VISUAL_MESH_LIMITATIONS.md
- VALIDATION_REPORT.json
- HASH_MANIFEST.json

Required model:
USD_PRIM -> HELSINKI_BUILDING_ID -> GMLID/RATU/VTJ_PRT/internal ID -> CER candidate -> SEG context -> evidence/limitations.

Boundary:
The semantic model may identify building objects. The photorealistic mesh is visual backdrop, not identity truth. Trees/cars/people/ships are not automatically graph entities.
