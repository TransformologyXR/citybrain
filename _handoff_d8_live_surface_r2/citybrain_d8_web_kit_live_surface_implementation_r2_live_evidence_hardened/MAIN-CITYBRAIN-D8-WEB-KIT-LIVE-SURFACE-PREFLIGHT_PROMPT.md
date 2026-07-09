# MAIN-CITYBRAIN-D8-WEB-KIT-LIVE-SURFACE-PREFLIGHT


Read `00_SHARED_CONTEXT.md` first. Operate inside `C:\Users\hazem\Documents\CityBrain`. Create a new output root under `outputs/` for this task. Do not stage or commit. Preserve review-only boundary and all no-action/no-mutation/secret/hash audits.


## Goal

Prove this implementation sprint is correctly anchored before touching Web/Kit code.

## Required checks

1. Locate latest green D8 Mobility-reanchored handoff:
   `PASS_MAIN_CITYBRAIN_D8_DEMONSTRABILITY_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS`.
2. Locate latest Mobility Access certified/handoff roots and D8 scoreboard facts.
3. Confirm hero spine = `Mobility Access corridor`.
4. Confirm NYC construction hero is parked and not a dependency.
5. Inventory existing UI/Kit prototype artifacts:
   - web control-room shells under `outputs/`
   - bridge app shells under `outputs/`
   - Kit selection/viewport/camera extension packages under `outputs/`
6. Inspect repo for existing source app conventions (`apps/`, `packages/`, `frontend/`, `web/`, `kit/`, `package.json`, etc.).
7. Decide source promotion layout. Default if none found:
   - `apps/web-control-room/`
   - `apps/kit/citybrain.control_room/`
   - `packages/contracts/`
   - `packages/fixtures/mobility_access/`
8. Probe local launch/runtime capabilities and write `LOCAL_RUNTIME_CAPABILITY_PROBE.json`:
   - Python available for local static server.
   - Node/browser/headless browser availability, if any, for DOM evidence.
   - Omniverse Kit executable/runtime availability.
   - Explicit `kit_runtime_available: true/false` with discovered path or reason.
9. Create `WEB_KIT_LIVE_SURFACE_PREFLIGHT_REPORT.json`.
10. Create `SOURCE_PROMOTION_PLAN.md` and `EXISTING_SURFACE_INVENTORY.json`.
11. Create `SURFACE_BASELINE_FREEZE_POLICY.md` explaining that `apps/` and `packages/` are maintained source, while the freeze is a baseline snapshot for capture/validation, not permanent immutability.

## Hard fail

Fail if D8 handoff is missing, if the plan tries to build NYC construction as the active spine, or if the plan requires internet package installation, or if the plan allows Web closeout based on instructions without live launch evidence.

## Decision status

Pass as:
`PASS_MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_PREFLIGHT_WITH_LIMITATIONS`
only if the sprint can proceed locally with the Mobility Access corridor and clean boundary.
