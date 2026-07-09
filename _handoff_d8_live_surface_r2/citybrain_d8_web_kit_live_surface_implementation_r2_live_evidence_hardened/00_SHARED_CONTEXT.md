# CityBrain D8 Web + Kit Live Surface Implementation — Shared Context

Generated: 2026-07-01
Workspace target: `C:\Users\hazem\Documents\CityBrain`
Pack status: prompt pack for next implementation sprint after `PASS_MAIN_CITYBRAIN_D8_DEMONSTRABILITY_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS`.

## Why this exists

D8 proved the Mobility Access corridor is internally demonstrable:

- Hero spine: `Mobility Access corridor`
- NYC construction hero: parked post-D8, not built
- Committed moments: 12
- Demonstrable moments: 10
- Documented partial: 2 (`M04`, `M05`)
- Pass rate: 0.833
- Boundary audits: PASS

Codex inspection of the actual repo surfaced the next bottleneck: recent D8 work generated binding maps, manifests, scoreboards, audits, and handoff collateral, but did not make the Web UI and Omniverse Kit extension first-class maintained product surfaces. Existing UI/Kit code is mostly prototype/generated under `outputs/`.

This sprint turns the architecture into a local, drivable, synchronized Web + Omniverse Kit demonstrator over the certified Mobility Access corridor, without adding new domain/city/perception/simulation substrate.


## R2 hardening: live surface means launched surface

This pack has been hardened to avoid the recurring failure mode where generated source, reports, and schemas pass green but no person has actually launched the surface.

For this sprint:

- Web is mandatory live evidence: local server started, page loaded, certified runtime bundle consumed, and a known Mobility Access value rendered in DOM/screenshot evidence.
- Kit launch is mandatory **if Omniverse Kit is runnable** on the machine. If Kit is not runnable, record `KIT_RUNTIME_UNAVAILABLE` as an explicit limitation and do not claim native Kit live launch.
- `one_truth_index.json` is the single authority; Web and Kit are projections of it.
- Capture readiness requires moment parity against the D8 scoreboard.
- The freeze is a baseline snapshot for validation, not a permanent write-lock on maintained source.
- Default web implementation is structured vanilla HTML/CSS/JS; no React/Vite/Next or internet package installs in this sprint.

## Non-negotiable boundary

This remains local/LAN/replay/review/query context only.

No production/public API claim. No auth/RBAC/security-hardening claim. No autonomous monitoring. No alerts. No dispatch. No routing/control. No enforcement. No legal/certified finding. No official ticket/case. No automated action. Track D remains authoritative for proposal/promotion lifecycle. `execution_state = not_executed` must remain visible in the UI and Kit surfaces.

## Product principle

Do not build more substrate. Promote and wire the surfaces that make the already-certified Mobility Access spine visible:

- one canonical runtime bundle
- one Web control-room source app
- one native Kit extension source package
- one local bridge / file-watch protocol
- one truth across Web, Kit, trace, option sets, D7 evidence, Track D packets, limitations, and capture state

## Source promotion principle

Prototype/generated files under `outputs/` may be copied/adapted into first-class source locations. Do not mutate old output roots. Preserve lineage by recording source paths and copied hashes.

Suggested source layout, unless the repo already has better conventions:

```text
apps/web-control-room/
apps/kit/citybrain.control_room/
packages/contracts/
packages/fixtures/mobility_access/
```

Prefer dependency-light implementation that runs offline from the current repo. If Node/React/Vite are already present, use existing conventions. If not, create a minimal static web app with vanilla JS/TypeScript-compatible modules and a Python local server/smoke. Do not require internet package installation.

## Canonical runtime bundle

Create a versioned local bundle under `packages/fixtures/mobility_access/runtime_bundle/` and copy it into each relevant output root:

```text
scenario_state.json
review_state.json
evidence_bundle.json
option_sets.json
trace.jsonl
track_d_packets.json
kit_overlay_packets.json
claim_labels.json
moment_scoreboard.json
limitations.json
one_truth_index.json
```

The bundle must be derived from the latest certified Mobility Access / D8 handoff outputs. Do not invent missing fields. If M04/M05 baseline/abstain fields are still absent, keep them documented partial.

## Allowed local bridge commands

Allowed commands: `select`, `scrub`, `inspect`, `camera`, `capture`, `focus`, `highlight`, `clear_highlight`.

Forbidden commands: `execute`, `dispatch`, `route`, `enforce`, `approve`, `create_ticket`, `create_case`, `send_alert`, `control_signal`, `legal_find`, `certify_finding`.

Any forbidden command must be rejected, logged, and shown as a boundary feature.
