# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-EVIDENCE-JOIN-R8

## Objective

Create a bounded narration-to-evidence join from the proven R2 candidate event and the R7 VSS narration sidecar.

## Inputs

Required input packages:

```text
R2: METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip
R7: METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip
```

Minimum lineage expected from R7:

```text
R7 status: PASS_METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_WITH_LIMITATIONS
R2 candidate observations/events: 24 / 1
Candidate event: metropolis-vss-r2-event-001
R2 source_class: sensor_inferred
VSS sidecar records: 1
VSS sidecar source_class: model_generated_narrative
VSS fact-source status: false
Candidate event mutated by VSS: false
```

## Scope

R8 may:

- read the R2 candidate event lineage
- read the R7 narration sidecar
- create a joined evidence bundle
- create a human review packet
- create a source-class separation audit
- create a CHECK/source-depth report
- create a closeout decision and freeze ZIP

R8 may not:

- rerun DeepStream
- rerun VSS
- change the R2 candidate event
- promote VSS prose into facts
- create a violation/finding/ticket/case/action/dispatch/control output
- infer identity, biometric attributes, readable IDs, or legal conclusions

## Target status

PASS:

```text
PASS_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_WITH_LIMITATIONS
```

PARTIAL:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_INPUT_MISSING_OR_INCOMPLETE
```

FAIL:

```text
FAIL_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_BOUNDARY_OR_SOURCE_CLASS_VIOLATION
```

## Acceptance summary

PASS requires:

```text
R7 PASS lineage present
R7 sidecar count >= 1
R2 candidate event unchanged
joined evidence bundle emitted
human review packet emitted
source_class separation PASS
CHECK/source-depth PASS
no-action PASS
claim-boundary PASS
secret audit PASS
hash manifest PASS
```
