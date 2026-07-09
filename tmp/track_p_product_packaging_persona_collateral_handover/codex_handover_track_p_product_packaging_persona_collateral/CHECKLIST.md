# Track P Checklist

## Before running

- Confirm the Hero Neighbourhood Control Room Reference Demo Closeout R1 is green.
- Confirm the integration-readiness review is green.
- Confirm the package is run in its own thread, separate from Track A and Track D.

## P0 preflight should verify

- Required upstreams discovered.
- Frozen demo facts loaded.
- Non-blocking gaps copied forward.
- Personas scoped as rendering policies, not agents.
- Collateral scope is packaging only.
- No mutation to upstream outputs.

## P1 persona R1 should produce

- Persona policy schema.
- Executive rendering policy.
- Operator rendering policy.
- Planner rendering policy.
- Analyst rendering policy.
- Shared evidence invariants.
- Persona anti-drift audit.

## P2 collateral R1 should produce

- Operator walkthrough script.
- Executive walkthrough script.
- Persona walkthrough notes.
- Claim-label audit.
- README / repo handoff draft.
- Capture checklist.
- Collateral manifest.
- Evidence and limitation trace summary.

## P3 closeout should verify

- All P0/P1/P2 artifacts present.
- Persona policies align to the same evidence and limitations.
- Collateral does not over-claim relative to frozen demo truth.
- Non-blocking gaps are included in README / scripts.
- No action/production/legal/certified/citywide claims.
- Hash manifest passes.

## Report back

- Final status.
- Output root.
- Persona count.
- Collateral artifact count.
- Required upstream count.
- Claim/no-action/no-mutation/secret/hash audit statuses.
- Blocking/non-blocking gaps.
- Recommended next task.
