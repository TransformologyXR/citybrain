# MAIN-CITYBRAIN-D8-HELSINKI-USD-PRIM-IDENTITY-SIDECAR-R2

Goal: build a bounded source-backed sidecar for Kit object selection.

For each sampled building:
- source building id / GMLID
- RATU / VTJ_PRT / ID if present
- display name/address if available
- measured height / use / construction year if present
- generated or actual USD prim path
- CER candidate id
- SEG/context fields
- limitations

Outputs:
- HELSINKI_USD_PRIM_TO_BUILDING_ID_SIDECAR.json
- HELSINKI_BUILDING_FACT_CARDS.json
- HELSINKI_VISUAL_IDENTITY_LIMITATIONS.md

Do not claim photorealistic mesh objects like trees/cars/ships have semantic identity unless a source says so.
