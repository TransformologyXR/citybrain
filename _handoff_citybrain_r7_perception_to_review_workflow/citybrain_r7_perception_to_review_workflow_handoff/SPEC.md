# SPEC — MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT

## Objective

Define and start the next sprint after R6: perception/VSS/Metropolis/DeepStream candidate observations plus official workflow draft/proposal handling.

## Product rule

```text
perception output = candidate observation
candidate observation = review input
review state = human/local
case/ticket = draft/sandbox unless explicitly approved
dispatch/control/enforcement = proposal only
execution_status = not_executed by default
```

## Scope

R7 covers:

1. Perception candidate observation ingress.
2. Candidate observation to CityBrain event packet mapping.
3. Human review promotion gate.
4. Draft case/ticket workflow adapter.
5. Dispatch/control/enforcement proposal object.
6. End-to-end replay/local smoke.

## Non-goals

R7 does not claim:

- production live monitoring
- official violation/legal finding
- autonomous ticket creation
- direct dispatch/control/enforcement execution
- public/cloud streaming
- safety-critical control
- production security/auth/RBAC
- final certified affected-building/asset determination

## Required data contracts

### CandidateObservation

Minimum fields:

- `candidate_observation_id`
- `source_system`
- `source_type`
- `camera_or_sensor_id`
- `media_ref`
- `frame_ref` or `clip_ref`
- `timestamp`
- `location_ref`
- `detected_classes`
- `confidence`
- `zone_ref`
- `evidence_refs`
- `limitation_refs`
- `review_state`
- `no_action_state`
- `cannot_claim`
- `packet_hash`

### ReviewPromotion

Minimum fields:

- `promotion_id`
- `candidate_observation_id`
- `reviewer_state`
- `reviewer_note`
- `promotion_target`
- `evidence_refs`
- `limitations`
- `approval_state`
- `created_at`
- `audit_hash`

### DraftCaseTicket

Minimum fields:

- `draft_id`
- `draft_type`
- `linked_candidate_observation_id`
- `subject_entity_id`
- `proposed_summary`
- `evidence_refs`
- `limitations`
- `cannot_claim`
- `reviewer_note`
- `submission_status`
- `submission_adapter`
- `no_action_state`

### ActionProposal

Minimum fields:

- `proposal_id`
- `proposal_type`
- `linked_draft_id`
- `allowed_action_type`
- `proposed_by`
- `approval_required`
- `approval_state`
- `execution_status`
- `prohibited_autonomy_audit`
- `rollback_or_cancel_note`
- `audit_hash`

## Acceptance criteria

PASS only if:

- candidate observations are packetized
- frame/clip/source provenance exists
- CHECK/claimability audit passes
- human review promotion gate is enforced
- draft case/ticket packet is generated as local/sandbox draft
- action proposal remains `not_executed`
- no direct official submission/execution occurs
- WebUI/Kit review surface can display candidate observation + draft/proposal status
- boundary audit passes
- tests and hash manifest pass

## Expected statuses

- `PASS_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS`
- `PASS_R7B_HUMAN_REVIEW_PROMOTION_GATE_WITH_LIMITATIONS`
- `PASS_R7C_CASE_TICKET_DRAFT_WORKFLOW_ADAPTER_WITH_LIMITATIONS`
- `PASS_R7D_ACTION_PROPOSAL_APPROVAL_BOUNDARY_WITH_LIMITATIONS`
- `PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS`
- `PARTIAL_R7_PERCEPTION_OUTPUT_ONLY_NO_REVIEW_PROMOTION`
- `PARTIAL_R7_WORKFLOW_DRAFT_ONLY_NO_PERCEPTION_RUNTIME`
- `FAIL_R7_AUTONOMOUS_ACTION_OR_OFFICIAL_CLAIM_REGRESSION`
