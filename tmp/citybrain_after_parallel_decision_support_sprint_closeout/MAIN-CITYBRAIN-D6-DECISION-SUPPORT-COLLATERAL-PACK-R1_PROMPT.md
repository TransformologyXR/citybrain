# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1

You are implementing:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-COLLATERAL-PACK-R1`

Goal:

Create the outward-facing collateral package for the decision-support sprint after integration readiness is green.

This is packaging only. It must not implement new runtime behavior and must not alter upstream facts.

Required upstream:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CASCADE-INTEGRATION-READINESS-REVIEW`

Expected output root:

`outputs/main_citybrain_d6_decision_support_collateral_pack_r1/`

Expected files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_COLLATERAL_PACK_R1_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `COLLATERAL_MANIFEST.json`
- `COLLATERAL_MANIFEST.jsonl`
- `EXECUTIVE_WALKTHROUGH.md`
- `OPERATOR_WALKTHROUGH.md`
- `TECHNICAL_WALKTHROUGH.md`
- `CLAIM_LABELS.md`
- `SAFE_TALKING_POINTS.md`
- `FORBIDDEN_TALKING_POINTS.md`
- `OPTION_SET_STORYBOARD.md`
- `CASCADE_STORYBOARD.md`
- `GOVERNED_9_STAGE_TRACE_SUMMARY.md`
- `HITL_BOUNDARY_SUMMARY.md`
- `LIMITATIONS_REGISTER.md`
- `VISUAL_CAPTURE_CHECKLIST.md`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Required disclosed facts:
- reviewed option-set count
- candidate option count
- do-nothing baseline preserved
- abstain/no-safe-option preserved
- Plan Mode/SUMO refs labelled context
- similar-case refs labelled context
- inverse dynamics options labelled review-only
- cascade refs labelled context
- Track D proposal lifecycle boundary preserved
- governed 9-stage runtime is a state-machine contract/smoke, not nine LLMs
- execution states are `not_executed`

Success status:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_COLLATERAL_PACK_R1_WITH_LIMITATIONS`

Failure status:

`FAIL_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_COLLATERAL_PACK_R1`
