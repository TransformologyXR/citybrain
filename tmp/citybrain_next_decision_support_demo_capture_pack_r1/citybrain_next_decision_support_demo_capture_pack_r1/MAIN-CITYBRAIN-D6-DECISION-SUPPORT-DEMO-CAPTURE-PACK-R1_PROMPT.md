# MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-R1

## Objective

Create a capture-ready collateral package for the green decision-support demo.

This is packaging only. Do not implement new runtime behavior.

## Required outputs

Output root:

`outputs/main_citybrain_d6_decision_support_demo_capture_pack_r1/`

Required files:
- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `FROZEN_FACTS_RECONCILIATION.json`
- `CAPTURE_STORYBOARD.md`
- `OPERATOR_WALKTHROUGH_SCRIPT.md`
- `EXECUTIVE_WALKTHROUGH_SCRIPT.md`
- `SHOT_LIST.json`
- `CAPTURE_ARTIFACT_MANIFEST.jsonl`
- `CLAIM_LABEL_CARDS.md`
- `LIMITATIONS_DISCLOSURE.md`
- `BOUNDARY_TALKING_POINTS.md`
- `DEMO_RUNBOOK.md`
- `LOCAL_OPEN_INDEX.md`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

## Must disclose

Disclose:
- local/replay review/query context only
- decision-support option sets are not recommendations to execute
- do-nothing baseline is present
- abstain/no-safe-option state is supported
- Track D remains authoritative after human promotion
- execution state remains `not_executed`
- SUMO/sim refs are context, not certified truth
- similar-case refs are context, not precedent mandates
- cascade attachments are context, not certified impact
- governed runtime trace is contract/trace harness, not production runtime

## Acceptance

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1_WITH_LIMITATIONS`
