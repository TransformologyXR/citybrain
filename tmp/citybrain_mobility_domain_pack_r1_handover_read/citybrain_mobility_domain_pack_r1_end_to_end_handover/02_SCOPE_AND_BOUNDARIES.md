# 02 — Scope and Boundaries

## In scope

- inventory mobility inputs
- draft and instantiate mobility entity catalog
- draft and instantiate mobility relationship catalog
- draft mobility event type catalog
- build mobility domain packet schema
- create mobility domain packets from available evidence/context
- create mobility episode candidates
- create R7 edge extension candidates
- create Track2A/Kit overlay handoff candidates where supported
- create D6/web companion handoff candidates where supported
- create limitation register
- create smoke and negative tests

## Out of scope

- production traffic model
- certified SUMO model
- live mobility feed ingestion
- traffic signal control
- routing control
- dispatch or enforcement
- public API
- production runtime
- event fabric implementation
- Omniverse event overlay implementation


## Permanent boundaries

Do not claim:
- production readiness
- public deployment
- certified traffic model
- certified impact
- route control
- dispatch
- enforcement
- legal finding
- confirmed violation
- autonomous monitoring or alerts
- source ID legal/ownership/certified truth
- observed truth from simulation/synthetic
- external LLM as truth engine

Do not:
- mutate source roots
- mutate D6 roots
- mutate Track 2A roots
- mutate Track 2B/2C roots
- mutate R5/R6/R7 roots
- mutate source USD/USDAs
- launch/control Omniverse unless already implemented and explicitly documented
- expose a public API
- implement production runtime
- create command/action/control artifacts

All writes must remain under the new output root.
