# PROMPT — MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT

You are Codex continuing CityBrain from the frozen R2 certified-state handover.

## Task

Create the decision-support option-set contract preflight.

Task name:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT`

Expected status on success:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_OPTION_SET_CONTRACT_PREFLIGHT_WITH_LIMITATIONS`

Expected output root:

`outputs/main_citybrain_d6_decision_support_option_set_contract_preflight/`

Expected runner:

`scripts/run_main_citybrain_d6_decision_support_option_set_contract_preflight.py`

## Purpose

Define the typed decision-support object before any Plan Mode, SUMO, inverse-dynamics, retrieval, or cascade generator produces option sets.

The core object is:

`reviewed_option_set`

It must be the shared packet used by later tracks:
- Plan Mode / SUMO
- inverse dynamics
- similar-case retrieval
- cross-domain cascade
- governed 9-stage runtime
- Track D HITL promotion bridge

## Load-bearing composition rules

### 1. Option is not Proposal

An `option` is a pre-review candidate inside `reviewed_option_set`.

A `proposal` is a Track D HITL object after human promotion into the approval lifecycle.

Therefore:

- `candidate_options[]` contains options.
- `proposal_refs[]` points to Track D proposal objects if/when promoted.
- The option set does not redefine Track D proposal schema.
- Track D remains authoritative for proposal approval/review lifecycle after promotion.
- `review_state_rollup` in the option set is a mirror/summary only.

### 2. D4Y decision-support relationship

Do not create an ambiguous second "decision support" meaning.

Define:

- D4Y decision-support / insight components = upstream signal/generator inputs.
- D6 `reviewed_option_set` = normalized decision-support output contract.
- Track D HITL proposal = governance lifecycle after promotion.

D4Y is not superseded. It can feed/generate/score inputs for option sets.

## Required top-level reviewed_option_set fields

Create a JSON schema that includes at least:

- `schema_version`
- `option_set_id`
- `scenario_ref`
- `scenario_state_ref`
- `valid_as_of`
- `trigger_event_ref`
- `affected_entity_refs`
- `desired_outcome_ref`
- `option_set_outcome`
- `candidate_options`
- `do_nothing_baseline_option_id`
- `comparison_axes`
- `tradeoff_basis`
- `evidence_refs`
- `simulation_refs`
- `graph_refs`
- `similar_case_refs`
- `generator_refs`
- `proposal_refs`
- `confidence_summary`
- `review_state_rollup`
- `allowed_action_types`
- `blocked_action_types`
- `guardrail_results`
- `human_review_required`
- `execution_state`
- `limitation_refs`
- `audit_refs`
- `claim_boundary`

Required `option_set_outcome` enum:

- `options_available`
- `no_safe_reviewed_option`
- `insufficient_evidence`
- `simulation_unavailable`
- `requires_human_escalation`

Required `execution_state` enum for this contract:

- `not_executed`

Do not allow any other execution state in this preflight.

## Required candidate_option fields

Create a JSON schema that includes at least:

- `schema_version`
- `option_id`
- `option_type`
- `option_role`
- `generation_method`
- `generator_ref`
- `description`
- `intended_outcome`
- `required_human_decision`
- `predicted_benefits`
- `predicted_costs`
- `risks`
- `dependencies`
- `comparison_values`
- `simulated_effect_summary`
- `simulation_version`
- `simulation_params_ref`
- `evidence_refs`
- `graph_refs`
- `similar_case_refs`
- `guardrail_results`
- `review_state`
- `promotion_eligibility`
- `proposal_ref`
- `not_executed_reason`
- `limitation_refs`
- `provenance`

Required `option_role` enum:

- `do_nothing_baseline`
- `candidate_intervention`
- `abstain_or_escalate`

## Mandatory baseline and abstain states

The do-nothing baseline must be mandatory in every `options_available` set.

A first-class abstain/no-safe-option representation must exist. Do not treat abstain as an error.

## Required examples

Produce at least 4 example option sets:

1. options available with do-nothing baseline and two candidate interventions.
2. no safe reviewed option exists.
3. insufficient evidence.
4. simulation unavailable but human escalation possible.

Every example must keep `execution_state = not_executed`.

## Expected files

- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_OPTION_SET_CONTRACT_PREFLIGHT_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `REVIEWED_OPTION_SET_SCHEMA.json`
- `CANDIDATE_OPTION_SCHEMA.json`
- `OPTION_SET_ENUMS.json`
- `TRACK_D_PROPOSAL_COMPOSITION_RULES.md`
- `D4Y_DECISION_SUPPORT_RELATIONSHIP.md`
- `OPTION_SET_EXAMPLES.json`
- `CONTRACT_VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Validation

Pass only if:

- schemas parse cleanly.
- examples validate against schemas.
- do-nothing baseline is mandatory.
- no-safe-option / abstain state exists.
- Track D proposal boundary is explicit.
- D4Y decision-support relationship is explicit.
- all execution states are `not_executed`.
- claim boundary audit passes.
- no-action audit passes.
- no-mutation audit passes.
- secret audit passes.
- hash validation passes.

## Boundary

No production, no public API, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no official case/ticket, no legal/certified conclusion, no automated action.
