# MAIN-CITYBRAIN-D8-KIT-CONTROL-ROOM-EXTENSION-SOURCE-PROMOTION-R2


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Promote existing generated Omniverse Kit extension prototypes into a first-class native Kit extension source package for the Mobility Access corridor.

## Build

Create or update:

```text
apps/kit/citybrain.control_room/
apps/kit/citybrain.control_room/config/extension.toml
apps/kit/citybrain.control_room/citybrain/control_room/extension.py
apps/kit/citybrain.control_room/citybrain/control_room/runtime_bundle.py
apps/kit/citybrain.control_room/citybrain/control_room/overlay_manager.py
apps/kit/citybrain.control_room/citybrain/control_room/selection_inspector.py
apps/kit/citybrain.control_room/citybrain/control_room/trace_panel.py
apps/kit/citybrain.control_room/citybrain/control_room/track_d_panel.py
apps/kit/citybrain.control_room/citybrain/control_room/capture_controls.py
apps/kit/citybrain.control_room/README.md
```

If the repo already has a better Kit extension convention, adapt and document.

## Required Kit capabilities

- Load/read the canonical runtime bundle.
- Build entity/prim binding lookup from `kit_overlay_packets.json`.
- Show overlay states for Mobility Access entities.
- Selection inspector resolves selected entity to evidence, option set, trace stage, limitations.
- Trace panel shows 9 governed stages.
- Track D panel shows promotion stop and `not_executed` boundary.
- Capture/camera controls are local review/capture only.
- Forbidden actions are not commands in the extension.

## Validation

- Extension config parses.
- Python files compile.
- Bundle loader unit smoke passes.
- Create `KIT_RUNTIME_PROBE_REPORT.json` first. If a Kit executable/runtime is discoverable, run a real extension load smoke and capture a log line proving the extension enabled. If unavailable, create `KIT_RUNTIME_UNAVAILABLE_REPORT.json` with exact reason and mark `kit_live_launch_status = NOT_RUN_KIT_RUNTIME_UNAVAILABLE`; do not imply native Kit live launch. Manual instructions may supplement evidence but cannot replace a runnable Kit smoke when Kit is available.
- If Kit runtime is unavailable, source validation may pass with limitations, but closeout/freeze must preserve the limitation explicitly and cannot claim Kit was live-launched.

Required artifacts:
```text
KIT_RUNTIME_PROBE_REPORT.json
KIT_EXTENSION_LOAD_SMOKE_REPORT.json OR KIT_RUNTIME_UNAVAILABLE_REPORT.json
KIT_EXTENSION_LOG_EXCERPT.txt if runtime smoke ran
```

## R2 hard fail

Fail this stage if Kit is available but the extension is not actually loaded/smoked, or if the report hides an unavailable Kit runtime behind generic run instructions. If Kit is unavailable, pass only with the explicit `NOT_RUN_KIT_RUNTIME_UNAVAILABLE` limitation while keeping source/package validation PASS.

## Outputs

```text
KIT_SOURCE_PROMOTION_REPORT.json
KIT_EXTENSION_VALIDATION_REPORT.json
KIT_BOUNDARY_AUDIT.json
KIT_LOCAL_RUN_INSTRUCTIONS.md
```

## Decision status

`PASS_MAIN_CITYBRAIN_D8_KIT_CONTROL_ROOM_EXTENSION_SOURCE_PROMOTION_R2_WITH_LIMITATIONS`
