# Checklist — Governed 9-Stage Runtime Contract Smoke R1

Run only after Cross-Domain Cascade is green.

Acceptance checklist:
- Required upstream discovery includes Track S, Track B, Track R, Track I, Decision-Support handover, and Cross-Domain Cascade closeout/freeze.
- Runtime contract smoke implements/stubs RECALL, PLAN, VALIDATE_PLAN, EXECUTE, NORMALIZE, SYNTHESIZE, RESOLVE_ACTIONS, SUGGEST, COMPLETE as deterministic stage interfaces.
- It proves stage I/O over existing option-set artifacts without building a production service.
- EXECUTE only means local/replay simulator/optimizer/retrieval/cascade contract calls or fixture reads; no real-world action.
- SYNTHESIZE is the only narration-eligible stage and must be grounded on EvidenceBundle/option-set artifacts.
- RESOLVE_ACTIONS maps only to HITL proposal bridge candidates; it does not approve, execute, dispatch, or enforce.
- Negative tests block nine-LLM/agent-swarm interpretation and auto-execution-shaped payloads.
- Claim-boundary audit PASS.
- No-action audit PASS.
- No-mutation audit PASS.
- Secret audit PASS.
- Hash manifest PASS.
- Blocking gaps = 0.
