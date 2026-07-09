# D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1

## Mission

Perform a bounded smoke test that aligns the Kalasatama CityGML-derived USD/CER sidecar candidates to the available visual backdrop / USD / 3D Tiles / Kit handoff context, proving a small sample of object-selection packets without claiming full canonical identity, legal truth, or citywide twin readiness.

This is a smoke test, not a full alignment pass.

## Starting context

The previous task passed:

`PASS_D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_WITH_LIMITATIONS`

Known outputs:

- CityGML identity spine consumed: `2,980 / 2,980` buildings.
- CER candidate map rows: `2,980`.
- USD/CER sidecar candidate rows: `2,980`.
- WFS bbox probe preserved as probe-only: `7,460`.
- WFS sample materialized: `100`.
- HSL mobility context: `274` stop candidates, `107` route candidates, `126,178` trip candidates.
- Energy sheets classified: `4`; `1 exact` sampled key match, `3 probable`.
- Visual mesh status: `VISUAL_BACKDROP_ONLY`.
- No legal/certified/production/live/autonomous/VSS claim.

## Inputs to inspect

Use local outputs only:

- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/CITYGML_BUILDING_IDENTITY_NORMALIZATION.csv`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/CITYGML_TO_CER_CANDIDATE_MAP.jsonl`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/USD_CER_SIDECAR_CANDIDATE_MAP.jsonl`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/VISUAL_MESH_BOUNDARY_NOTE.md`
- visual backdrop root if present:
  - `outputs/d4_3d_helsinki_kalasatama_3d_tiles_landing_r1/`
- any existing Web+Kit or Omniverse handoff folders that can consume sidecar metadata

If the visual backdrop is absent, run a metadata-only sidecar smoke and mark visual alignment as blocked.

## Required output root

Create:

`outputs/d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/`

## Required artifacts

1. `SIDECAR_ALIGNMENT_SAMPLE_SELECTION.json`
   - Select a bounded sample of 12 to 25 buildings.
   - Selection should include:
     - deterministic first records
     - varied bbox/height/geometry records if available
     - at least one record with strong explicit source IDs where available
   - Include reason for each sample.

2. `USD_CER_ALIGNMENT_SMOKE_PACKETS.jsonl`
   - One packet per sample.
   - Include:
     - candidate_prim_path
     - suggested_prim_name
     - canonical_entity_candidate_id
     - linked_citybrain_candidate_id
     - source_citygml_id
     - source_record_ref
     - geometry_ref
     - visual_backdrop_ref if available
     - evidence_refs
     - limitation_refs
     - binding_status
     - review_state

3. `KIT_COMPOSER_HANDOFF_LAYER.usda`
   - Lightweight USDA marker/metadata layer if feasible.
   - Must not mutate source USD/3D Tiles/CityGML.
   - If USDA generation is not feasible, create `KIT_COMPOSER_HANDOFF_LAYER_NOT_CREATED.md` with reason.

4. `SIDE_CAR_ALIGNMENT_SMOKE_REPORT.md`
   - Explain what was proven and what remains unproven.
   - Distinguish:
     - CityGML semantic identity candidate
     - CER candidate
     - suggested USD prim path
     - visual mesh backdrop
     - actual object-level alignment

5. `VISUAL_BACKDROP_ALIGNMENT_STATUS.json`
   - Fields:
     - visual_backdrop_present
     - source_visual_root
     - object_level_alignment_proven
     - smoke_sample_count
     - source_mutation
     - limitations

6. `HELSINKI_USD_SIDECAR_ALIGNMENT_SMOKE_DECISION.json`
   - Final decision:
     - task_id
     - status
     - sample_count
     - packets_created
     - usda_layer_created
     - visual_backdrop_present
     - object_level_alignment_claim_made
     - hard_errors
     - limitations
     - next_recommended_task

7. `LOCAL_OPEN_INDEX.md`
   - Links to all created artifacts.

8. Hash/audit outputs:
   - `HASH_MANIFEST.json`
   - `hashes.sha256`
   - `JSON_PARSE_AUDIT.json`
   - `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
   - `SECRET_AUDIT.json`
   - `CLAIM_BOUNDARY_AUDIT.json`

## Acceptance criteria

The task passes if:

- A bounded sample of sidecar candidates is selected deterministically.
- Alignment smoke packets exist and preserve evidence/limitation refs.
- A lightweight Kit/Composer handoff layer is produced or a clear blocked reason is recorded.
- Source USD/3D Tiles/CityGML are not mutated.
- The task does not claim full canonical identity or visual mesh object-level alignment unless directly proven for the sample.
- Visual backdrop remains backdrop-only unless sample alignment evidence supports a stronger local/sample claim.
- JSON artifacts parse clean.
- Hashes verify.

## Expected status

Use:

`PASS_D4_HELSINKI_KALASATAMA_USD_SIDECAR_ALIGNMENT_SMOKE_R1_WITH_LIMITATIONS`

unless no meaningful sidecar packet can be produced.

## Forbidden claims

Do not claim:

- full Helsinki or full Kalasatama canonical acceptance
- legal/certified building identity
- full object-level alignment
- full citywide twin
- production Omniverse readiness
- live operational state
- autonomous action/control/dispatch/enforcement
