# 05 — Acceptance Gates

## Full R1 pass

`PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS`

Minimum gates:
- at least 10 mobility entity types
- at least 10 mobility relationship types
- at least 8 mobility event types
- at least 12 mobility domain packets
- at least 8 mobility episode candidates
- at least 8 R7 edge extension candidates
- at least 6 D6/product handoff candidates
- at least 6 Track2A/Kit handoff candidates
- evidence refs where available
- limitation refs on every packet/candidate
- no_action_taken on every packet/candidate
- audits PASS

## DATA_FIRST pass

`PASS_MOBILITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS`

Use this if:
- source coverage is too thin for rich domain packets
- but entity/relationship/event catalog, DATA_FIRST packet scaffold, and candidate handoffs are still useful

Minimum gates:
- entity/relationship/event catalog exists
- DATA_FIRST register exists
- at least 6 mobility domain packet scaffolds
- all limitations explicit
- no fabricated traffic state
- audits PASS

## Waiting status

`WAITING_ON_MOBILITY_INPUT_ROOTS`

Use only if there is not enough context to build even a bounded DATA_FIRST mobility domain pack.
