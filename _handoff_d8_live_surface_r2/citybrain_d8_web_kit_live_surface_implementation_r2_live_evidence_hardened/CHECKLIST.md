# Checklist

## Required before starting

- D8 Mobility-reanchored demonstrability handoff is green.
- Current certified hero spine is Mobility Access corridor.
- NYC construction hero remains parked.
- No new city/domain/perception/simulation substrate is authorized.

## Required outputs by closeout

- First-class source paths created or updated:
  - `apps/web-control-room/`
  - `apps/kit/citybrain.control_room/`
  - `packages/contracts/`
  - `packages/fixtures/mobility_access/`
- Canonical runtime bundle exists and validates.
- Web control room **must actually launch locally** and render the Mobility Access spine, with DOM/screenshot evidence containing a known certified bundle value.
- Kit extension package validates and, if Kit is available, loads/smokes in a real Kit runtime with captured log proof. If unavailable, `KIT_RUNTIME_UNAVAILABLE` is recorded explicitly and the freeze must not imply Kit live launch.
- Local bridge supports allowed commands and rejects forbidden commands.
- Web/Kit one-truth drift checks pass **against `one_truth_index.json` as authority**.
- Capture readiness manifest exists and `LIVE_SURFACE_MOMENT_PARITY_REPORT.json` maps every D8 demonstrable moment to a live render home.
- Claim/no-action/no-mutation/secret/hash audits pass.

## Hard failures

- Creating NYC construction hero substrate.
- Inventing missing do-nothing or abstain fields.
- Adding production/public API/auth/RBAC/security hardening claims.
- Allowing execute/dispatch/route/enforce/approve commands.
- UI or Kit surfaces hiding `not_executed` or Track D authority boundary.
- Marking capture-ready without a real local Web launch smoke and moment parity report.

- Passing closeout/freeze on Web run instructions only, with no launch evidence.
- Treating a source baseline freeze as a permanent write-lock on maintained app source.
