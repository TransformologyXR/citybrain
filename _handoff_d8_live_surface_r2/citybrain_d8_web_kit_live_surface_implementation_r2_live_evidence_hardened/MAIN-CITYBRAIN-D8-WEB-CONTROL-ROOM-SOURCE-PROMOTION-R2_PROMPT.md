# MAIN-CITYBRAIN-D8-WEB-CONTROL-ROOM-SOURCE-PROMOTION-R2


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## R2 technology decision

Default to structured vanilla HTML/CSS/JS for this sprint. Do not introduce React, Vite, Next.js, package-manager installs, or internet dependencies. This is a maintained source app, but it must remain dependency-light, locally runnable, hashable, and auditable.

## Goal

Promote the best existing generated web prototype into a first-class local source app and wire it to the canonical runtime bundle.

## Build

Create or update `apps/web-control-room/`.

Minimum source structure:

```text
apps/web-control-room/index.html
apps/web-control-room/src/main.js
apps/web-control-room/src/runtimeBundle.js
apps/web-control-room/src/views/situation.js
apps/web-control-room/src/views/options.js
apps/web-control-room/src/views/trace.js
apps/web-control-room/src/views/evidence.js
apps/web-control-room/src/views/trackD.js
apps/web-control-room/src/views/limitations.js
apps/web-control-room/src/views/capture.js
apps/web-control-room/src/bridge/client.js
apps/web-control-room/README.md
```

If the repo already has a maintained web stack, adapt to it instead and explain why.

## Required UI panels

- Situation overview for Mobility Access corridor.
- Event / evidence / D7 candidate observations panel.
- Option-set comparison over 3 option sets / 7 options where present.
- Governed 9-stage trace panel.
- Track D promotion stop panel: eligible, non-promotion, `not_executed`, no approvals.
- Limitations and claim labels visible in-demo.
- Persona toggle if persona render facts exist; otherwise visible `not_available` reason.
- Capture checklist panel.

## Validation

- Static source validation: all referenced runtime-bundle files load.
- HTML/JS parse sanity.
- Section coverage test: required panels present.
- Boundary text test: no forbidden claims; `not_executed` visible.
- No internet dependencies.



## R2 required live Web launch evidence

This task must not pass on source existence alone.

Create and run a local launch smoke:

```text
scripts/run_main_citybrain_d8_web_control_room_local_launch_smoke.py
```

Minimum evidence:

- Start a local static server for `apps/web-control-room/` using Python or another already-local tool.
- Load the Web control room against the certified Mobility Access runtime bundle.
- Assert a known certified value appears in the rendered surface, for example one of:
  - `execution_state = not_executed`
  - D7 candidate observations count = `6`
  - operator trace stages = `9`
  - option-set attachments = `3`
  - cross-city similar cases = `4`
- Produce DOM scrape evidence and/or screenshot evidence. If an automated browser is available, use it. If not, use a deterministic render harness from the same Web source and record the limitation, but still prove HTTP/local launch and rendered known values.

Required artifacts:

```text
WEB_LOCAL_LAUNCH_EVIDENCE.json
WEB_RENDERED_DOM_ASSERTION_REPORT.json
WEB_LAUNCH_SCREENSHOT_OR_DOM_CAPTURE.*
```

Hard fail: no `PASS` if Web evidence is only `WEB_LOCAL_RUN_INSTRUCTIONS.md`. The launch evidence and DOM assertion reports must exist and pass.

## Outputs

```text
WEB_SOURCE_PROMOTION_REPORT.json
WEB_PANEL_COVERAGE_REPORT.json
WEB_BOUNDARY_AUDIT.json
WEB_LOCAL_RUN_INSTRUCTIONS.md
WEB_LOCAL_LAUNCH_EVIDENCE.json
WEB_RENDERED_DOM_ASSERTION_REPORT.json
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_WEB_CONTROL_ROOM_SOURCE_PROMOTION_R2_WITH_LIMITATIONS`
