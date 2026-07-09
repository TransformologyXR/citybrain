# MAIN-CITYBRAIN-D8-MOBILITY-ACCESS-LIVE-SURFACE-WIRING-R4


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Wire the Mobility Access certified spine into the Web and Kit surfaces so the scenario can be driven as one local demo.

## Required flow

The local flow must render the following without manual packet-loading:

```text
scenario loads
-> Mobility Access entities/relationships render
-> D7 candidate observations show as evidence candidates
-> option sets and comparison axes show where present
-> governed 9-stage trace is watchable
-> Track D promotion packets show eligibility and stop
-> limitations visible
-> one bridge command selection updates Web and Kit coherently
```

## Moment coverage target

Wire the 10 demonstrable D8 moments from the D8 scoreboard. Keep M04/M05 partial unless fields exist. Every wired moment must point to a real runtime-bundle ref.

## Validation

Create a scripted smoke that drives at least:

- select one entity
- inspect evidence
- show D7 candidate observation
- show option comparison
- show 9-stage trace
- show Track D stop
- attempt forbidden command and confirm rejection
- capture/readiness marker

## Outputs

```text
MOBILITY_ACCESS_SURFACE_WIRING_REPORT.json
DEMO_FLOW_SMOKE_REPORT.json
MOMENT_REF_RESOLUTION_REPORT.json
SURFACE_SCREENSHOT_OR_CAPTURE_PLACEHOLDER_LEDGER.json
```

This stage may use screenshot/capture placeholders only as a readiness ledger. The later capture pass must require real media.

## Decision status

`PASS_MAIN_CITYBRAIN_D8_MOBILITY_ACCESS_LIVE_SURFACE_WIRING_R4_WITH_LIMITATIONS`


## R2 moment-home preparation

While wiring the live surface, emit a preliminary `MOMENT_RENDER_HOME_INDEX.json` that maps each D8 demonstrable moment to its Web panel, Kit overlay/selection behavior if applicable, bridge command path if applicable, claim label, limitation label, and capture shot candidate. R6 will use this as the source for moment parity.

Do not create synthetic render homes for M04/M05 if the underlying baseline/abstain fields are absent. Keep them `documented_partial`.
