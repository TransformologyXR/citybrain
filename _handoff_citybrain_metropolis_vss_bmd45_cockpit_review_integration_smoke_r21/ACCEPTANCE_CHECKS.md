# ACCEPTANCE CHECKS — R21

## Input checks

- R20 package present.
- R20 final status is accepted.
- R20 hash manifest verifies.
- R20 human-review packet present.
- R20 cockpit fixture present.
- R20 source/audit boundaries pass.

## Output checks

- Integration packet emitted.
- Tile fixture emitted.
- Frame cards emitted.
- Review action policy emitted.
- App handoff manifest emitted.
- External media refs preserved.
- JSON parse clean.
- Hash manifest clean.

## Boundary checks

- No live CCTV claim.
- No official finding.
- No ticket/case.
- No dispatch/control/enforcement.
- No identity or biometric inference.
- No legal/certified claim.
- VSS remains not a fact source.
- Dataset annotations remain dataset_annotation.
- DeepStream remains sensor_inferred.
