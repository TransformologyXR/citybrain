# MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-R1

Objective:
Build a bounded local/replay Mobility Access Domain Pack R1.

Required capabilities:
- mobility_access domain metadata
- entity refs for corridor, route segment, lane/kerbside/access context
- relationship families for route access, lane/kerbside constraint, pedestrian/mobility context, incident/cascade context
- evidence refs and limitation refs
- domain-specific safe action types mapped to reviewed option-set allowed actions
- blocked actions mapped to no-action boundary

Outputs:
- `MOBILITY_ACCESS_DOMAIN_PACK_R1.json`
- `MOBILITY_ACCESS_ENTITY_BRIDGE.json`
- `MOBILITY_ACCESS_RELATIONSHIP_BRIDGE.json`
- `MOBILITY_ACCESS_ACTION_POLICY.json`
- `VALIDATION_REPORT.json`
- audits and hash manifest

Must not:
- create route/control commands
- claim traffic optimization truth
- claim live traffic management
- mutate R7/R8/CER/SEG or Track D

Pass status:
`PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_R1_WITH_LIMITATIONS`
