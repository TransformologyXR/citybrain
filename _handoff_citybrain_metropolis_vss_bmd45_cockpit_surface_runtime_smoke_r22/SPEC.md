# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-SURFACE-RUNTIME-SMOKE-R22

## Objective

Launch or exercise a bounded cockpit surface/runtime consumer against the R21
BMD-45 cockpit review fixture.

The goal is to prove that the operator-facing surface can consume:

- `COCKPIT_REVIEW_TILE_R21.json`
- `FRAME_REVIEW_CARDS_R21.json`
- `COCKPIT_APP_FIXTURE_R21.json`
- `HUMAN_REVIEW_PACKET_CONSUMPTION_FIXTURE_R21.json`
- external media references
- source-class and boundary labels

without changing source semantics or claiming live CCTV.

## In scope

- Local web/app route smoke if the cockpit app exists.
- Static render/HTML/JSON viewer fallback if the app route is unavailable.
- Fixture loading and schema validation.
- Review tile/card rendering smoke.
- Boundary-label visibility checks.
- External-media-reference link preservation.
- Source-class label preservation.
- No-action/no-ticket/no-dispatch/no-identity/no-legal-claim assertions.
- Screenshot/DOM/text snapshot if feasible.

## Out of scope

- DeepStream rerun.
- VSS rerun.
- BMD-45 frame re-fetch unless required only to validate external media refs.
- Live RTSP/CCTV.
- Production UI readiness.
- Official case/ticket workflow.
- Dispatch/control/action.
- Identity or biometric inference.

## Target final status

`PASS_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_RUNTIME_SMOKE_R22_WITH_LIMITATIONS`

## Acceptable partial

`PARTIAL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_CONTRACT_READY_APP_RUNTIME_PENDING`

## Failure statuses

- `FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_BOUNDARY_BREACH_R22`
- `FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_SOURCE_CLASS_DRIFT_R22`
- `FAIL_METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_APP_CONSUMPTION_R22`
