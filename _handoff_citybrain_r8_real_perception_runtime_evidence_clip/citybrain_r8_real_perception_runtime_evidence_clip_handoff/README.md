# CityBrain R8 Real Perception Runtime + Evidence Clip Handoff

Task:

```text
MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION
```

Purpose:

Move from R7's fixture/sandbox perception-to-review smoke into a real local/replay perception runtime lane.

R8 should connect real or replay video input to a DeepStream/Metropolis/VSS-style runtime, produce candidate observations, export frame/clip evidence, and feed the existing CityBrain WebUI/Kit review workflow.

Hard boundary:

```text
runtime perception = candidate observation only
evidence frames/clips = review evidence, not legal proof
case/ticket = draft/sandbox only
dispatch/control/enforcement = proposal only
execution_status = not_executed
```
