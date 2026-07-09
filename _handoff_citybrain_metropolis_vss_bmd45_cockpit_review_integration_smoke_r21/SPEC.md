# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-REVIEW-INTEGRATION-SMOKE-R21

## Objective

Consume the accepted R20 human-review benchmark packet and emit an app/cockpit-facing integration fixture for operator review.

## Product purpose

R20 proved that benchmark results can be shaped into human-review packets. R21 proves that those packets can be handed to the cockpit layer safely.

## Required input

- `METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_PACKAGE.zip`
- R20 final status: `PASS_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_WITH_LIMITATIONS`

## Required output

- cockpit review integration packet
- cockpit tile fixture
- frame-card fixture set
- external media reference manifest
- review action policy
- app handoff manifest
- boundary/audit reports
- closeout decision
- hash manifest

## Target status

`PASS_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_WITH_LIMITATIONS`

## Acceptable partial

`PARTIAL_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_CONTRACT_READY_APP_SURFACE_PENDING`

Use the partial status if no app/cockpit surface is available and only fixture validation is possible.

## Hard boundaries

- Do not claim live CCTV.
- Do not create official findings.
- Do not create tickets/cases.
- Do not dispatch, route, enforce, or control.
- Do not identify people or infer biometrics.
- Do not treat VSS as a fact source.
- Do not treat BMD-45 annotations as official truth.
- Do not treat DeepStream detections as findings.

## Source classes

- BMD-45 labels: `dataset_annotation`
- DeepStream/Metropolis candidates: `sensor_inferred`
- VSS: `model_generated_narrative_not_fact_source`

