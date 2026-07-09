# ENTRY PROMPT — Operator Decision-Support Surface R1

Task: `MAIN-CITYBRAIN-D6-OPERATOR-DECISION-SUPPORT-SURFACE-R1`

You are running the operator-surface continuation of the current Decision-Support Intelligence Sprint.

Do not start unless `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-CLOSEOUT` and preferably `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-MILESTONE-FREEZE` are green. If Cross-Domain Cascade is missing or not green, fail safely with upstream_missing and do not create a partial surface.

Goal:
Create a bounded operator-facing decision-support surface packet layer over the already-green decision-support artifacts. This is not a new generator, not a new proposal lifecycle, and not a production UI. It should assemble review-safe operator packets that display option sets, tradeoffs, SUMO context, similar-case context, cascade context, Track D promotion boundary, and limitations.

Inputs to discover:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-MILESTONE-FREEZE`
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH`
- `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-MILESTONE-FREEZE` if present
- Track D HITL reviewed-action milestone freeze

Produce output root:
`outputs/main_citybrain_d6_operator_decision_support_surface_r1/`

Create runner:
`scripts/run_main_citybrain_d6_operator_decision_support_surface_r1.py`

Required output files:
- `MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_DECISION.json`
- `README.md`
- `LOCAL_OPEN_INDEX.md`
- `INPUT_ARTIFACT_INDEX.json`
- `OPERATOR_DECISION_SUPPORT_SURFACE_SCHEMA.json`
- `OPERATOR_DECISION_SUPPORT_PACKETS.json`
- `OPERATOR_DECISION_SUPPORT_PACKETS.jsonl`
- `OPTION_SET_SURFACE_BINDINGS.json`
- `TRADEOFF_DISPLAY_MATRIX.json`
- `TRACK_D_PROMOTION_BOUNDARY_DISPLAY.json`
- `CONTEXT_REF_DISPLAY_INDEX.json` covering SUMO, similar-case, cascade, evidence, graph, and limitation refs
- `SURFACE_VALIDATION_REPORT.json`
- `NEGATIVE_TEST_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Required surface behavior:
- preserve do-nothing baseline
- preserve abstain/no-safe-option
- display candidate interventions as review-only
- display comparison axes consistently
- display Track D promotion as optional human-review bridge only
- preserve `execution_state = not_executed`
- include limitation labels for SUMO, similar-case, cascade, USD/twin context, and local/replay scope
- do not create approved proposals
- do not create alerts, dispatches, official cases, enforcement actions, routing/control actions, or legal/certified claims

Decision status on success:
`PASS_MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_WITH_LIMITATIONS`

Decision status on failure:
`FAIL_MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1`

After completion, report status, output root, packet count, option-set binding count, upstreams found/required, blocking gaps, non-blocking gaps, and next recommended task.
