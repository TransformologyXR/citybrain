# MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1

## Mission

Smoke-test consumption of the D8 Web+Kit demo bundle using the latest governed evidence, including mobility-abstain semantics and Helsinki/Kalasatama sidecar readiness where available, without turning the web or Kit surfaces into unsupported production/live/autonomous claims.

This is a local consumption smoke, not a new product build.

## Starting context

Known current state:

- D8 Web+Kit live surface implementation pack superseded earlier Web+Kit pack and uses structured vanilla HTML/CSS/JS by default.
- Web local launch evidence is a hard gate.
- Web/Kit demo bundle from parallel readiness scout status: `PASS_WITH_LIMITATIONS`, read-only projection generated.
- D8 demonstrability has 12 committed moments, 10 demonstrable, M04/M05 documented partial but now ready for render via field-presence scan.
- Helsinki context consumption prep passed:
  - 2,980 CityGML building identity rows consumed
  - 2,980 CER candidate rows
  - 2,980 USD/CER sidecar candidate rows
  - visual mesh status `VISUAL_BACKDROP_ONLY`
  - next task `D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1`
- This task must consume, not overclaim.

## Inputs to inspect

Use available local outputs only. Prefer these roots/files where present:

- `outputs/main_citybrain_d8_web_kit_live_surface_implementation_r2_live_evidence_hardened/`
- any D8 Web+Kit bundle output root from the parallel readiness scout
- `outputs/main_citybrain_d8_parallel_data_readiness_closeout/DATA_READINESS_SCOREBOARD.json`
- `outputs/main_citybrain_d8_parallel_data_readiness_closeout/PARALLEL_DATA_READINESS_CLOSEOUT_DECISION.json`
- mobility abstain contract patch output if already present:
  - `outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/`
- Helsinki sidecar prep output if present:
  - `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/`
  - `USD_CER_SIDECAR_CANDIDATE_MAP.jsonl`
  - `VISUAL_MESH_BOUNDARY_NOTE.md`
- existing D8 local open indexes and demo moment registries

If a parallel task output is absent, mark it as pending and proceed with a limitation.

## Required output root

Create:

`outputs/main_citybrain_d8_web_kit_bundle_consumption_smoke_r1/`

## Required artifacts

1. `WEB_KIT_CONSUMPTION_SMOKE_PLAN.md`
   - Define what will be consumed.
   - Define what is explicitly out of scope.
   - Include local-only/read-only boundary.

2. `WEB_CONSUMPTION_FIXTURE_MANIFEST.json`
   - List all web fixture/data files consumed.
   - Include source output root, hash if available, and limitation refs.

3. `KIT_CONSUMPTION_FIXTURE_MANIFEST.json`
   - List all Kit/Omniverse/USDA/USD/sidecar candidate files consumed.
   - If no real Kit/Composer is launched, mark as `handoff_manifest_only`.
   - Include Helsinki sidecar candidate map if present.

4. `MOMENT_RENDER_CONSUMPTION_STATUS.json`
   - One row per D8 committed moment.
   - Include:
     - moment_id
     - source evidence refs
     - web render status
     - kit/handoff render status
     - limitation refs
     - blocked/partial reason
   - M04/M05 must respect mobility-abstain contract if available.

5. `LOCAL_WEB_LAUNCH_SMOKE_RESULT.json`
   - If web launch is possible locally:
     - command
     - host/port
     - HTTP status
     - checked routes/files
     - screenshot path if produced
   - If web launch is not possible:
     - safe skip reason
     - files still validated
   - Do not require internet package installs.

6. `KIT_HANDOFF_SMOKE_RESULT.json`
   - If Kit/Composer is available:
     - scene/layer opened
     - prim/metadata checks
     - selected sample count
   - If not available:
     - handoff-only validation result
     - sidecar/USDA syntax/file checks
   - Must preserve visual-backdrop-only limitation for Helsinki.

7. `WEB_KIT_CLAIM_BOUNDARY_COPY.md`
   - Safe UI/demo copy:
     - web is companion evidence/episode/executive surface
     - Kit/Composer is spatial control-room/handoff surface where available
     - no live monitoring/production/autonomous/control/legal/certified claim

8. `D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_DECISION.json`
   - Final decision:
     - task_id
     - status
     - web_consumed
     - kit_consumed_or_handoff_validated
     - moments_checked
     - mobility_abstain_contract_seen
     - helsinki_sidecar_seen
     - hard_errors
     - limitations
     - next_recommended_task

9. `LOCAL_OPEN_INDEX.md`
   - Links to all created artifacts.

10. Hash/audit outputs:
   - `HASH_MANIFEST.json`
   - `hashes.sha256`
   - `JSON_PARSE_AUDIT.json`
   - `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
   - `SECRET_AUDIT.json`
   - `CLAIM_BOUNDARY_AUDIT.json`

## Acceptance criteria

The task passes if:

- Web/Kit bundle files are consumed or explicitly classified as missing/pending.
- Web local launch is attempted only if no unsafe dependency install is required.
- Kit is validated as actual Kit/Composer smoke if available, otherwise as handoff-only smoke.
- M04/M05 do not overclaim mobility baseline validity.
- Helsinki sidecar candidates remain candidates and visual mesh remains backdrop-only.
- All product copy has safe boundaries.
- Prior certified outputs are not mutated.
- JSON artifacts parse clean.
- Hashes verify.

## Expected status

Use:

`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_BUNDLE_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS`

unless hard local file/runtime failures prevent even fixture-level validation.

## Forbidden claims

Do not claim:

- production web app
- live city monitoring
- full Kit/Composer runtime unless actually opened/proven
- full Omniverse citywide twin
- object-level identity acceptance for Helsinki mesh
- certified mobility baseline
- autonomous routing/control/dispatch/enforcement
- legal/certified/government decisioning
