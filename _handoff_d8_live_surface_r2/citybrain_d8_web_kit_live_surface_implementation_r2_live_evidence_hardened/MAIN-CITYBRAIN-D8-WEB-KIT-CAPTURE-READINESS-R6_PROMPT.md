# MAIN-CITYBRAIN-D8-WEB-KIT-CAPTURE-READINESS-R6


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Prepare the newly maintained Web + Kit surfaces for the later live capture/media pass.

## Build

Create a capture readiness package that states exactly how to capture the local demo:

- Web URL or local path.
- Kit extension path and launch instructions.
- Runtime bundle path.
- Bridge inbox/outbox path.
- Operator cut shot list.
- Executive cut shot list.
- Per-moment clip manifest template.
- Claim labels that must be visible per shot.
- Limitation labels that must be visible per shot.



## R2 required moment parity gate

This stage must prove the maintained surface has a render home for the D8 demonstrable moments before the next capture/viewer sprint starts.

Create `LIVE_SURFACE_MOMENT_PARITY_REPORT.json` by reading the D8 scoreboard and the `MOMENT_RENDER_HOME_INDEX.json` from R4.

For every D8 moment with `demonstrability_status = demonstrable` or equivalent green status, require:

- moment id and label
- data_basis ref resolved to certified runtime bundle
- Web render home: panel id / route / DOM selector
- Kit render home if spatial/overlay relevant, or explicit `kit_not_required_for_this_moment` reason
- bridge command path if interaction is required
- claim label visible
- limitation label visible
- capture shot id in operator or executive shot list

For D8 documented partials (`M04`, `M05` unless later proven), preserve partial status and do not fabricate missing option-set baseline/abstain fields.

Hard fail: fewer than the D8 green/demonstrable moments have render homes, or any render home lacks a certified data basis.

## Important

This stage does not claim that real media exists. It only proves the surfaces are ready to capture. The later follow-through pack must require actual media files.

## Outputs

```text
CAPTURE_READINESS_REPORT.json
OPERATOR_CAPTURE_SHOT_LIST.md
EXECUTIVE_CAPTURE_SHOT_LIST.md
MOMENT_CLIP_MANIFEST_TEMPLATE.json
CLAIM_LABEL_VISIBILITY_CHECKLIST.json
LIVE_SURFACE_MOMENT_PARITY_REPORT.json
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_CAPTURE_READINESS_R6_WITH_LIMITATIONS`
