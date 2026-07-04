# ASK v1.1 Contradiction Candidate Review

## Summary

No candidate is ready for R2 as a valid retained real-corpus contradiction.

## Screened Candidates

### screened-a5-grounding-gate-status-v2-v3

- Source A: `outputs/a5d1_operator_query/hero_single_record/hero_parcel_1010607502_grounded_gate_v2.json`
- Source B: `outputs/a5d1_operator_query/hero_single_record/hero_parcel_1010607502_grounded_gate_v3.json`
- Entity/ref: `gate_id:A5-NARRATION-GROUNDED`
- Claim field: `status`
- Assertion A: `FAIL`
- Assertion B: `PASS`
- Readiness: not ready

Why screened out:

Both files share a gate id and rule, but they evaluate different narration artifacts. The v2 report points at `hero_parcel_1010607502_nemo_nim_narration_v2.md`; the v3 report points at `hero_parcel_1010607502_nemo_nim_narration_v3.md`. This is a versioned QA progression, not a same-claim contradiction.

Possible later use:

If a retained-data addition explicitly frames these as competing retained assertions about one unresolved gate target, ASK should cite both and not choose a winner. Until then, keep it out of R2 ready coverage.

### screened-mobility-bridge-command-status

- Source A: `packages/fixtures/mobility_access/bridge/outbox/cmd-allowed-scrub-001.event.json`
- Source B: `packages/fixtures/mobility_access/bridge/outbox/cmd-forbidden-dispatch-001.event.json`
- Entity/ref: `scenario_state:mobility-access-corridor:hero-lon-corridor`
- Claim field: `command_status`
- Assertion A: `accepted`
- Assertion B: `rejected`
- Readiness: false positive

Why screened out:

The statuses belong to different commands and different action shapes. This supports boundary/action guardrail coverage, not contradiction.

### screened-a5-permit-status-per-parcel

- Source A: `outputs/a5d1_operator_query/evidence_bundles/q01_parcel_profile_d98017ca.json`
- Source B: `outputs/a5d1_operator_query/evidence_bundles/q02_building_profile_8732bb8f.json`
- Entity/ref: `parcel:us-nyc:bbl:1010607502` / `building:us-nyc:bin:1026676`
- Claim field: `permit_status`
- Assertions: multiple statuses such as `ISSUED`, `APPROVED`, `PERMIT ENTIRE`, and `LOC ISSUED`
- Readiness: false positive

Why screened out:

The values refer to different permit jobs linked to the same parcel/building. The exact permit canonical IDs did not show conflicting `permit_status` values.

### screened-flow-or-package-lifecycle-status

- Source A/B: multiple retained decision, closeout, and flow ledger JSON artifacts
- Entity/ref: various flow/package IDs
- Claim field: `status` / `final_status`
- Assertions: `not_accepted_requires_flow_acceptance_gate`, `accepted_*`, `PASS`, `FAIL`, `PASS_WITH_LIMITATIONS`
- Readiness: false positive

Why screened out:

These are implementation lifecycle states across different packages. They are not retained city-source records and generally represent progression rather than contradiction.

## R2 Disposition

Use a formal real-corpus contradiction waiver for R2 unless the user authorizes a retained-data addition before R2.
