# ENTRY PROMPT — Decision-Support Demo Capture Pack R1

You are Codex continuing CityBrain after the Runtime Trace + Demo Polish sprint closed green.

Run this package as a sequential, packaging-only lane.

Start with:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-R1`

Then, if the R1 package is green, run:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-CLOSEOUT`

## Task intent

Turn the already-green decision-support sprint into a capture-ready outward artifact. This should package the demo story; it should not change the underlying runtime, option-set, trace harness, HITL, cascade, or decision-support truth path.

## Required upstreams

Find and consume, read-only:
- `outputs/main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh`
- `outputs/main_citybrain_d6_runtime_trace_demo_polish_final_package_review`
- `outputs/main_citybrain_d6_runtime_trace_demo_polish_integration_readiness_review`
- `outputs/main_citybrain_d6_decision_support_demo_polish_closeout`
- `outputs/main_citybrain_d6_governed_runtime_trace_harness_closeout`
- `outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh`
- `outputs/main_citybrain_d6_decision_support_control_room_demo_closeout_r1`
- `outputs/main_citybrain_d6_decision_support_milestone_freeze`

If an upstream is unavailable, record it explicitly. Do not invent paths.

## Outputs

Create:
- output root under `outputs/main_citybrain_d6_decision_support_demo_capture_pack_r1`
- runner under `scripts/run_main_citybrain_d6_decision_support_demo_capture_pack_r1.py`
- if closeout is run, output root under `outputs/main_citybrain_d6_decision_support_demo_capture_pack_closeout`
- closeout runner under `scripts/run_main_citybrain_d6_decision_support_demo_capture_pack_closeout.py`

## Pass condition

Pass only if:
- required upstreams are found or explicitly documented
- frozen counts reconcile
- capture storyboard exists
- operator and executive scripts exist
- claim labels and limitations are explicit
- manifest of capture artifacts exists
- no runtime implementation changes are made
- no-action/no-mutation/secret/hash/claim audits pass
