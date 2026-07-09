# MAIN-CITYBRAIN-D8-WEB-KIT-DEMO-ASSET-DATA-BUNDLE

Goal: create a small, complete demo data bundle that the Web+Kit live surface can consume without reading arbitrary outputs roots.

Inputs:
- D8 certified handoff
- Mobility Access runtime bundle if present
- Web+Kit live surface implementation outputs if present
- Helsinki pilot outputs if present

Outputs:
- DEMO_DATA_BUNDLE_MANIFEST.json
- one_truth_index.json or reference pointer
- scenario_state.json
- review_state.json
- evidence_bundle.json
- option_sets.json
- trace.jsonl
- track_d_packets.json
- kit_overlay_packets.json
- claim_labels.json
- moment_scoreboard.json
- limitations.json
- DEMO_DATA_BUNDLE_VALIDATION_REPORT.json
- HASH_MANIFEST.json

Rules:
- Bundle is a read-only projection of certified state.
- All values must have provenance refs.
- No UI-specific hardcoded truth.
- If Kit assets are not available, include KIT_ASSETS_UNAVAILABLE_REPORT.json rather than inventing prim bindings.
