# Prompt: DATA-GAP-LEDGER-AND-PRIORITY-MATRIX

You are running a CityBrain data-readiness scout. Do not ingest large datasets yet. Do not build features. Produce the data gap ledger first.

Current goal:
Create the authoritative data-gap and source-priority map for the next demonstrability/data sprint.

Inputs:
- Current certified Mobility Access / D8 outputs under `outputs/`.
- D8 demonstrability limitations: placeholder capture media, external viewer validation pending, M04/M05 partial unless option-set fields exist.
- City/source candidates: Helsinki 3D semantic twin, Singapore traffic images, Chicago violations/311/AoT, NYC post-D8 construction spine, London resilient city sources, Melbourne time-scrub sources, Dubai DLD/Makani.

Hard boundaries:
- No production/public API claim.
- No autonomous monitoring, alerting, dispatch, routing/control, enforcement, legal/certified finding, identity/biometric inference, or automated action.
- No large downloads in this task.
- No mutation of certified outputs.
- No invented option-set baseline/abstain fields.

Required outputs under:
`outputs/data_gap_ledger_and_priority_matrix/`

Files:
- `DATA_GAP_LEDGER.json`
- `DATA_SOURCE_PRIORITY_MATRIX.json`
- `SOURCE_ACCESS_STATUS.json`
- `LICENSE_AND_ATTRIBUTION_LEDGER.json`
- `BLOCKERS_AND_DEFERRED_DATASETS.md`
- `NEXT_DATA_LANDING_RECOMMENDATION.md`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Data sources to classify:
1. Helsinki semantic 3D / WFS / Kalasatama CityGML.
2. Singapore LTA / data.gov traffic images.
3. Chicago building violations, 311, Array of Things.
4. NYC PLUTO, DOB, collisions, EMS, 3D buildings — catalog only / post-D8 target.
5. London TfL, LFB, LAQN.
6. Melbourne pedestrian/parking time-series.
7. Dubai DLD, Makani, Data.Dubai.
8. VSS/Metropolis readiness: video corpus, runtime, output mapping.

For each source classify:
- `source_id`
- `official_url`
- `access_mode`: open_api | open_download | api_key_required | captcha_or_form_blocked | large_download | third_party_only | unknown
- `license_or_terms`
- `estimated_size`
- `identity_value`
- `moment_value`
- `demo_value`
- `risk`
- `recommended_action`: land_now | scout_only | defer | blocked

Priority rule:
1. Highest: Helsinki semantic twin pilot.
2. Then: Singapore/video readiness scout and VSS/Metropolis readiness.
3. Then: Mobility M04/M05 option-set gap check.
4. Then: Chicago similar-case enrichment.
5. NYC construction, London, Melbourne, Dubai are scout/catalog unless they are required by a committed D8 moment.

Decision status:
- PASS if the matrix exists, all known sources are classified, boundaries pass, no large download occurred.
- FAIL if it mutates upstream outputs, starts implementation, or makes production/live monitoring/action claims.
