# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-SPRINT-CLOSEOUT-R9

## Objective

Create the final sprint closeout package for the CityBrain Metropolis/VSS media-perception lane.

The closeout must consume the verified R1-R8 lineage, with R8 as the latest validated input, and freeze a single honest decision about what the sprint proved and what remains limited.

## Sprint proof target

```text
media / sample video
→ DeepStream / Metropolis sensor_inferred object metadata
→ candidate observations
→ candidate event
→ Spark VSS model_generated_narrative sidecar
→ joined EvidenceBundle
→ CHECK/source-depth validation
→ human review packet
```

## Host allocation to preserve

```text
txr-4070:
  DeepStream / Metropolis
  source_class = sensor_inferred
  proven by R2

spark-2445:
  Spark VSS / LVS / RT-VLM
  source_class = model_generated_narrative
  proven by R7/R8

txr-3090:
  inactive for this Metropolis/VSS chain
```

## Required closeout status

Preferred:

```text
PASS_METROPOLIS_VSS_MEDIA_CANDIDATE_OBSERVATION_AND_NARRATION_SPRINT_CLOSEOUT_WITH_LIMITATIONS
```

Allowed partial:

```text
PARTIAL_METROPOLIS_VSS_MEDIA_CANDIDATE_OBSERVATION_PROVEN_VSS_CONNECTED_NARRATION_PENDING
```

Failure:

```text
FAIL_METROPOLIS_VSS_SPRINT_CLOSEOUT_BOUNDARY_OR_SOURCE_CLASS_VIOLATION
```

## Non-negotiable boundaries

The R9 closeout must confirm:

- DeepStream / Metropolis remains `sensor_inferred`.
- Spark VSS remains `model_generated_narrative`.
- VSS is not a fact source.
- VSS does not mutate the R2 candidate event.
- No official record, ticket, dispatch, enforcement, legal/certified finding, identity inference, biometric inference, alert command, or automated action is created.
- Human review remains required.
- NVIDIA/NGC secrets are not packaged.

## Acceptance checks

R9 can PASS only if:

- R2/R7/R8 lineage is present and clean.
- R8 source-class separation is preserved.
- R8 candidate event hash is unchanged.
- R8 human-review packet is present.
- Final no-action audit is PASS.
- Final claim-boundary audit is PASS.
- Final secret audit is PASS.
- Final hash manifest is verified.
