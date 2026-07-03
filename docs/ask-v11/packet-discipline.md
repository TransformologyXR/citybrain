# ASK v1.1 Packet Discipline

ASK Flow v1.1 is a contracted packet pipeline:

```text
IntentPacket -> ExecutionContract -> EvidencePacket -> CheckReport -> AnswerPacket | ClarificationPacket
```

The raw user query is allowed only at the run boundary and in the G1/G2 input
surface. Downstream stages consume packets, never raw query text. That rule is
what keeps G3 a compiler rather than a planner: it can instantiate
registry-declared template contracts with validated arguments, but it cannot
reinterpret the user or invent a retrieval plan at runtime.

The flow envelope carries `stage_failures[]`, `degraded_response_decision`,
`stage_timings`, `trace_hops[]`, `packet_refs`, and `not_executed[]`. The
orchestrator shell may report degradation, clarification, no-data, or refusal,
but it may not silently patch a failed stage and continue as if the contracted
packet had existed.

CHECK is the G6 `CheckReport` engine. G7 and G8 must honor its downgrades,
abstains, contradictions, stale flags, and coverage limits. A normal
`AnswerPacket` must link to a `CheckReport`; without that linkage, there is no
claimable answer to render.
