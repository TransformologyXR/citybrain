# MAIN-CITYBRAIN-D14-STAGED-SCHEMA-CONTRACT-R1

## Goal
Define the staged router schema, replacing the unstable flat `expected_route_label` decision.

## Required design

### Stage A — Boundary / guard class
Closed vocabulary:
- `clear`
- `action_shaped`
- `prediction_or_finding`
- `identity_or_person`
- `out_of_scope_domain`
- `ambiguous_boundary`

Stage A is a guard, not a peer. Composition rule:
- If Stage A is `clear`, continue to Stage B/C/D/E.
- If Stage A is non-clear, the router output must be refusal or boundary-explanation path. Later stages may be recorded as diagnostic/onward intent, but cannot route to city-answer template.
- `ambiguous_boundary` is allowed for multi-valent questions such as “Can we tell drivers this charger is unavailable?” and should render a claimability answer wrapped with a boundary note if deterministic support exists, or a boundary explanation/refusal when needed. It must never silently become an action template.

### Stage B — Intent family
Closed vocabulary:
- `city_subject_question`
- `source_record_question`
- `patch_queue_question`
- `meta_product_question`
- `external_context_question`
- `identity_person_question`
- `out_of_scope_question`

`meta_product_question` covers product/software/board-capability questions such as export, notes, whether the board can alert, whether it is official, or cyber/compliance posture. It is not a city-subject answer.

### Stage C — Route target within family
Closed vocabulary:
- `subject_answer`
- `entity_360`
- `source_record_360_gap`
- `patch_queue_query_gap`
- `external_context_source_gap`
- `ui_help`
- `boundary_explanation`
- `refusal`

### Stage D — Subject-answer lens
Only meaningful when Stage C = `subject_answer`.
Closed vocabulary:
- `support`
- `uncertainty`
- `claimability`
- `summary`
- `not_applicable`

Lens changes which section renders first; it does not change the assembled answer object.

### Stage E — Context requirement
Boolean: `requires_selected_item_context`.
True only if the question cannot be interpreted without the selected item/prior context.
False if it names the asset, board, patch, record, weather, ranking, police, export, legal finding, or item scope.

## Error pricing and gates
- Stage A: <= 5% disagreement, hard. Refusal-boundary hard errors <= 1, ideally 0.
- Stage B: <= 15% disagreement.
- Stage C: <= 20% disagreement.
- Stage D: <= 25% disagreement and non-blocking unless it changes output family.
- Stage E: <= 15% disagreement.
- Full-path exact agreement is informational only; do not use it as the primary gate.
- Report all-stage independent agreement and on-policy agreement separately.

## Output
Write:
- `STAGED_ROUTER_SCHEMA_CONTRACT_R1.json`
- `STAGED_ROUTER_DECISION_TREE_R1.md`
- `STAGED_ROUTER_GATE_POLICY_R1.json`

## Status
`PASS_D14_STAGED_SCHEMA_CONTRACT_R1`
