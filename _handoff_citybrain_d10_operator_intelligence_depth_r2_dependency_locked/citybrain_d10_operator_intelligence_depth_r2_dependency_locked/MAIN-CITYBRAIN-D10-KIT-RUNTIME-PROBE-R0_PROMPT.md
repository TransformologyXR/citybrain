# MAIN-CITYBRAIN-D10-KIT-RUNTIME-PROBE-R0

## Purpose
Run an early Omniverse Kit/Composer runtime environment probe.

D13 depends on this environment fact. Discover it now, not at D13 preflight.

## Probe only
This is not D13 feature work.

## Required checks
Where local environment permits:
- Is target machine / environment reachable?
- Does Kit/Composer exist or is it callable?
- Can a minimal extension/session load?
- Can a simple CityBrain relevant USD or placeholder open?
- Can the probe write logs/screenshot or headless evidence?
- Is GPU/driver/runtime available?
- What exact blocker exists if not?

## Output
`KIT_RUNTIME_PROBE_R0_REPORT.json`

Status values:
- `PASS_KIT_RUNTIME_PROBE_READY_FOR_D13_WITH_LIMITATIONS`
- `PARTIAL_KIT_RUNTIME_PRESENT_BUT_EXTENSION_LOAD_BLOCKED`
- `FAIL_KIT_RUNTIME_NOT_AVAILABLE`
- `SKIPPED_ENVIRONMENT_UNAVAILABLE_FOR_PROBE`

## Hard boundary
Do not claim spatial cockpit integration from this probe.
Do not alter D13 roadmap beyond recording readiness/blockers.
