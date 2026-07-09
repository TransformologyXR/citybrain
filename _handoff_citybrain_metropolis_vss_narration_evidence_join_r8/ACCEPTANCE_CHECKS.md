# ACCEPTANCE CHECKS — R8

## PASS checks

- R7 package validation PASS.
- R7 closeout status is `PASS_METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_WITH_LIMITATIONS`.
- R7 sidecar count is at least 1.
- R2 candidate event ID is preserved.
- R2 candidate event hash or mutation flag proves unchanged.
- Joined evidence bundle exists.
- Human review packet exists.
- VSS sidecar source class is `model_generated_narrative`.
- R2 structured source class is `sensor_inferred`.
- VSS is not fact source.
- No candidate event mutation.
- No official record/action/dispatch/ticket/control/legal finding.
- Claim-boundary audit PASS.
- Source-class separation audit PASS.
- CHECK source-depth audit PASS.
- Secret audit PASS.
- Hash manifest PASS.

## PARTIAL checks

Use partial if any required input package is missing, incomplete, or sidecar-free, while all boundaries remain safe.

## FAIL checks

Fail if any of the following occurs:

- VSS prose is promoted into detection fact.
- VSS changes R2 candidate event.
- VSS creates or confirms a violation/finding/action.
- Identity/biometric inference appears.
- Official case/ticket/dispatch/control wording appears.
- Secrets are packaged.
