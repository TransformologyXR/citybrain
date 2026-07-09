# MAIN-CITYBRAIN-D8-MOBILITY-BASELINE-ABSTAIN-CONTRACT-PATCH-R1

## Mission

Patch the D8 mobility baseline contract so M04/M05 can be rendered and consumed honestly from existing evidence while preserving abstain behavior where mobility baselines are not yet statistically/operationally justified.

This is a contract/evidence-safety patch. Do not build a new mobility engine, do not download new large data, do not claim baseline truth, and do not mutate certified prior outputs.

## Starting context

Known current state:

- D8 demonstrability certified state has 12 committed moments.
- 10 moments are demonstrable.
- M04 and M05 are documented partials but now marked ready for render from existing field-presence scan.
- Parallel readiness scout status: `PASS_MAIN_CITYBRAIN_D8_PARALLEL_DATA_READINESS_SCOUTS_WITH_LIMITATIONS`.
- Mobility option set status: `PASS_READY_FOR_RENDER`.
- The goal is not to invent mobility certainty. The goal is to make the product surface show the current mobility evidence with explicit abstain/limitation semantics.

## Inputs to inspect

Use available local outputs only. Prefer these roots/files where present:

- `outputs/main_citybrain_d8_parallel_data_readiness_closeout/DATA_READINESS_SCOREBOARD.json`
- `outputs/main_citybrain_d8_parallel_data_readiness_closeout/PARALLEL_DATA_READINESS_CLOSEOUT_DECISION.json`
- `outputs/data_gap_ledger_and_priority_matrix/DATA_GAP_LEDGER.json`
- `outputs/data_gap_ledger_and_priority_matrix/DATA_SOURCE_PRIORITY_MATRIX.json`
- any D8 demonstrability scoreboard / committed moments registry
- any M04/M05 field-presence scan outputs
- any existing web/kit bundle projection files that already reference M04/M05

If an expected input is absent, record that as a limitation and continue with best available local evidence.

## Required output root

Create:

`outputs/main_citybrain_d8_mobility_baseline_abstain_contract_patch_r1/`

## Required artifacts

1. `MOBILITY_BASELINE_ABSTAIN_CONTRACT.json`
   - Defines allowed mobility states:
     - `baseline_supported`
     - `baseline_abstained`
     - `ready_for_render_with_limitations`
     - `insufficient_evidence`
   - Defines required fields:
     - `moment_id`
     - `mobility_claim_type`
     - `evidence_refs`
     - `render_status`
     - `baseline_status`
     - `abstain_reason`
     - `limitation_refs`
     - `review_state`
   - Makes clear that render readiness is not baseline validity.

2. `M04_M05_MOBILITY_RENDER_READINESS_PATCH.json`
   - One entry per M04/M05 moment.
   - Include:
     - current evidence available
     - missing baseline requirements
     - render-ready evidence fields
     - explicit abstain text
     - safe UI label
     - unsafe/forbidden UI claims

3. `MOBILITY_BASELINE_ABSTAIN_UI_COPY.md`
   - Short, user-facing copy snippets for:
     - moment card
     - evidence drawer
     - limitation banner
     - executive summary
   - Must avoid any claim that CityBrain has proven actual mobility impact, live operations, optimization, enforcement, routing, or certified traffic baseline.

4. `MOBILITY_BASELINE_ABSTAIN_TEST_MATRIX.json`
   - Test cases for:
     - M04/M05 render allowed with limitation
     - no-data mobility case abstains
     - baseline-supported case remains possible for future
     - unsupported claim blocked
     - production/live/autonomous/routing/enforcement wording blocked

5. `D8_MOBILITY_BASELINE_ABSTAIN_PATCH_DECISION.json`
   - Final decision:
     - task_id
     - status
     - inputs_inspected
     - moments_patched
     - contract_created
     - tests_created
     - hard_errors
     - limitations
     - next_recommended_task

6. `LOCAL_OPEN_INDEX.md`
   - Links to all created artifacts.

7. Hash/audit outputs:
   - `HASH_MANIFEST.json`
   - `hashes.sha256`
   - `JSON_PARSE_AUDIT.json`
   - `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
   - `SECRET_AUDIT.json`
   - `CLAIM_BOUNDARY_AUDIT.json`

## Acceptance criteria

The task passes if:

- M04/M05 are renderable through a governed contract without being upgraded to proven mobility baselines.
- The contract explicitly separates:
  - field/evidence presence,
  - render readiness,
  - baseline validity,
  - abstain behavior.
- UI copy exists for safe product display.
- Unsafe claims are blocked.
- Prior certified outputs are not mutated.
- JSON artifacts parse clean.
- Hashes verify.

## Expected status

Use:

`PASS_MAIN_CITYBRAIN_D8_MOBILITY_BASELINE_ABSTAIN_CONTRACT_PATCH_R1_WITH_LIMITATIONS`

unless a required local input absence prevents any meaningful contract patch, in which case use a bounded fail status and preserve partial artifacts.

## Forbidden claims

Do not claim:

- live mobility monitoring
- certified traffic baseline
- measured traffic impact
- autonomous routing
- dispatch/control/enforcement
- legal/compliance conclusion
- production readiness
- citywide mobility truth
