# R22 Acceptance Checks

PASS requires:

- R21 input validation PASS.
- Cockpit tile loaded.
- Cockpit app fixture loaded.
- Frame review cards loaded.
- At least 8 frame review cards preserved.
- Source-class labels preserved.
- Boundary labels present in tile/cards or explicit UI fixture metadata.
- External media refs preserved and not packaged as media files.
- Consumption smoke PASS.
- All final audits PASS.
- Hash manifest verifies all packaged files.

Partial is acceptable if:

- Runtime/app route is unavailable,
- but the render fixture and package contract are ready.

FAIL if:

- source classes drift,
- VSS is treated as fact source,
- live CCTV is claimed,
- a finding/ticket/dispatch/action/legal/identity claim appears,
- or the R21 fixture cannot be loaded.
