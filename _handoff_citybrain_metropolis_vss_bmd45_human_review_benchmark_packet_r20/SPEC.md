# SPEC — R20 BMD-45 Human Review Benchmark Packet

## Task

`MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-HUMAN-REVIEW-BENCHMARK-PACKET-R20`

## Objective

Turn the verified R19 benchmark/regression harness into a review-ready packet for the CityBrain cockpit/app surface.

R20 should make the replay benchmark understandable to a human reviewer without changing the underlying evidence.

## Inputs

- R19 package: `METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_PACKAGE.zip`
- R19 baseline/rerun scorecard
- R19 sensor-inferred candidates
- R19 frame comparison records
- R19 external media refs
- R19 drift review packet
- R18/R19 threshold calibration metadata

## Must produce

- `R20_CLOSEOUT_DECISION.json`
- `R19_INPUT_LINEAGE_SUMMARY.json`
- `HUMAN_REVIEW_BENCHMARK_PACKET_R20.json`
- `COCKPIT_REVIEW_TILE_FIXTURE_R20.json`
- `FRAME_REVIEW_CARD_FIXTURES_R20.json`
- `BENCHMARK_SCORECARD_SUMMARY_R20.json`
- `FALSE_POSITIVE_REVIEW_LIST_R20.json`
- `MISSED_ANNOTATION_REVIEW_LIST_R20.json`
- `SOURCE_CLASS_SEPARATION_AUDIT_R20.json`
- `CLAIM_BOUNDARY_AUDIT_R20.json`
- `NO_ACTION_AUDIT_R20.json`
- `VSS_NOT_FACT_SOURCE_AUDIT_R20.json`
- `SECRET_AUDIT_R20.json`
- `HASH_MANIFEST.json`

## Target status

`PASS_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_WITH_LIMITATIONS`

## Acceptable partial

`PARTIAL_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_PACKET_CONTRACT_READY_APP_INTEGRATION_PENDING`

## Boundaries

- BMD-45 labels remain `dataset_annotation`.
- DeepStream/Metropolis outputs remain `sensor_inferred`.
- VSS remains `model_generated_narrative` and is not a fact source.
- This is not live CCTV.
- This is not a finding, legal/certified conclusion, ticket, dispatch, identity inference, or action.
