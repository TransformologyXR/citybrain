# CityBrain Metropolis/VSS — Narration Evidence Join R8 Handoff

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-EVIDENCE-JOIN-R8`

This handoff consumes the verified R7 PASS package and defines the next narrow join step.

R8 is not a new detection run and not a production monitoring run. It joins:

```text
R2 DeepStream/Metropolis candidate event
+ R7 Spark VSS narration sidecar
+ source-class separation
+ CHECK/source-depth validation
+ human review packet
```

The core rule remains:

```text
DeepStream / Metropolis = sensor_inferred candidate observation metadata.
Spark VSS = model_generated_narrative review context only.
VSS is not a fact source and must not mutate the candidate event.
```

R8 should emit a joined evidence bundle and human review packet that make both sources visible and separated.

