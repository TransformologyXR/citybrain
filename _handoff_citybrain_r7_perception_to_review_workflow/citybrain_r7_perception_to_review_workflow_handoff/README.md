# CityBrain R7 Perception → Review Workflow Handoff

Task:

```text
MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT
```

Purpose:

Define the next sprint after Omniverse/WebRTC R6.

R7 introduces perception/VSS/Metropolis/DeepStream as **candidate observation inputs**, then connects accepted human-reviewed candidates to **case/ticket/action proposal workflows**.

Important boundary:

```text
perception = candidate observation
case/ticket = draft or sandbox workflow object
dispatch/control/enforcement = proposal only unless a human explicitly approves in a sandbox/test adapter
actions = not_executed by default
```

This sprint must not claim live monitoring, final violation/legal determination, autonomous dispatch/control/enforcement, or production integration.
