# MAIN-CITYBRAIN-D6-MOBILITY-D7-TRACE-DOMAINPACK-SPRINT-INTEGRATION-READINESS-REVIEW

Objective: verify that the current sprint lanes align and can be closed together.

Required upstreams to discover:
- Mobility Access Domain Pack certified-state/handover refresh, or at minimum closeout + milestone freeze if the handover refresh has not been produced.
- D7 Perception Candidate Observation milestone freeze.
- Governed Operator Trace Panel closeout/freeze or latest green closeout.
- Promotion Panel + Domain-Pack Handoff integration readiness review.

Supporting upstreams to discover if present:
- D7 Perception Blueprint / Collateral Pack.
- Cross-city / cross-domain scout and cross-city similar-case expansion outputs.
- Multi-machine actual deployment rehearsal milestone freeze.
- Recent sprint certified-state handovers.

Produce:
- `INTEGRATION_READINESS_DECISION.json`
- `UPSTREAM_DISCOVERY.json`
- `SPRINT_ALIGNMENT_MATRIX.json`
- `BOUNDARY_CARRY_FORWARD_REVIEW.json`
- `LIMITATION_RECONCILIATION.json`
- `COUNT_RECONCILIATION.json`
- audits and hash manifest

Pass only if required upstreams are green and no blocking compatibility gaps exist.


Boundary: local/LAN/replay/review/query context only unless a specific bounded remote file sync is explicitly stated for the infra lane. No production/public API claim, no auth/RBAC/security-hardening claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no legal/certified finding, no official ticket/case, no automated action. Preserve all upstream outputs read-only. Generated outputs must be additive under outputs/ and no existing unrelated worktree changes may be modified.
