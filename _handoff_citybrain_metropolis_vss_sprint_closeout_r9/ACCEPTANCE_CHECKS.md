# ACCEPTANCE CHECKS — MAIN-CITYBRAIN-METROPOLIS-VSS-SPRINT-CLOSEOUT-R9

## PASS checklist

- [ ] R8 input package exists.
- [ ] R8 ZIP integrity PASS.
- [ ] R8 JSON parse PASS.
- [ ] R8 hash manifest PASS.
- [ ] R8 final status PASS.
- [ ] R2 structured source class is `sensor_inferred`.
- [ ] R7 VSS source class is `model_generated_narrative`.
- [ ] VSS fact-source flag is false.
- [ ] R2 candidate event hash unchanged.
- [ ] R2 candidate event not mutated.
- [ ] One joined EvidenceBundle is emitted or preserved.
- [ ] One human-review handoff is emitted or preserved.
- [ ] Source-class final audit PASS.
- [ ] Claim-boundary final audit PASS.
- [ ] No-action final audit PASS.
- [ ] VSS-not-fact-source final audit PASS.
- [ ] Secret audit PASS.
- [ ] Hash manifest PASS.
- [ ] Freeze ZIP readback PASS.

## Immediate FAIL conditions

- VSS prose is used to create or alter a detection fact.
- VSS prose is treated as official/sensor truth.
- The R2 candidate event is mutated.
- Any official case/ticket/action/dispatch/enforcement/legal finding is created.
- Identity/biometric inference is present.
- Secret/token/API key content is packaged.
