# MAIN-CITYBRAIN-D8-WEB-KIT-LIVE-SURFACE-CLOSEOUT


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Close the Web + Kit live surface implementation sprint.

## Required upstreams

- Preflight PASS
- Runtime bundle contract PASS
- Web source promotion PASS
- Kit extension source promotion PASS
- Local bridge / one-truth sync PASS
- Mobility Access live surface wiring PASS
- State drift + guardrail smoke PASS
- Capture readiness PASS

## Closeout checks

- Source files exist in first-class paths.
- Runtime bundle validates.
- Web UI renders required panels locally with `WEB_LOCAL_LAUNCH_EVIDENCE.json` PASS and `WEB_RENDERED_DOM_ASSERTION_REPORT.json` PASS. Run instructions are supplementary only and cannot substitute for launch evidence.
- Kit extension validates and either `KIT_EXTENSION_LOAD_SMOKE_REPORT.json` PASS exists, or `KIT_RUNTIME_UNAVAILABLE_REPORT.json` explicitly records Kit was not runnable. If Kit was unavailable, closeout must say `kit_live_launch_status = NOT_RUN_KIT_RUNTIME_UNAVAILABLE` and must not claim native Kit was live.
- Bridge accepts allowed commands and rejects forbidden commands.
- One-truth drift checks pass against `one_truth_index.json` as authority.
- Capture readiness exists, does not claim real media, and includes `LIVE_SURFACE_MOMENT_PARITY_REPORT.json` PASS for D8 demonstrable moments.
- No new substrate introduced.
- NYC construction remains parked.

## Outputs

```text
WEB_KIT_LIVE_SURFACE_CLOSEOUT_DECISION.json
IMPLEMENTED_SOURCE_INDEX.json
RUNTIME_BUNDLE_INDEX.json
OPEN_ISSUE_LEDGER.json
PARKING_LOT_POST_D8.json
WEB_LOCAL_LAUNCH_EVIDENCE_SUMMARY.json
KIT_RUNTIME_STATUS_SUMMARY.json
LIVE_SURFACE_MOMENT_PARITY_SUMMARY.json
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_CLOSEOUT_WITH_LIMITATIONS`


## R2 closeout hard fail

Do not close green if:

- Web was not actually launched locally.
- Web launch evidence is only instructions.
- A known certified bundle value was not observed in rendered DOM/screenshot/capture evidence.
- Drift checks compare surfaces only to each other and not to `one_truth_index.json`.
- R6 did not prove render-home parity for the D8 demonstrable moments.
- Kit unavailable status is hidden or described as a live Kit launch.
