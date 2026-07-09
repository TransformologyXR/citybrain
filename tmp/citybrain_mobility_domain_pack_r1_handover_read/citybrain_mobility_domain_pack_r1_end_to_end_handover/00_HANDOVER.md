# 00 — Handover

## Task

`MAIN-CITYBRAIN-D4X-MOBILITY-DOMAIN-PACK-R1-END-TO-END`

## Goal

Build the first bounded Mobility Domain Pack R1 end-to-end, advancing as far as current source/context availability allows.

This task should not stop at a planning-only preflight unless core inputs are genuinely missing. It should include preflight/inventory as Phase 0, then continue into implementation artifacts:

```text
input inventory
→ mobility entity/relationship/event model
→ mobility domain packet schema
→ sample mobility domain packets
→ mobility episode candidates
→ R7 edge candidates/extensions
→ Track 2A/Kit handoff candidates
→ D6/product handoff candidates
→ smoke/audit/decision
```

## Why this is one task now

The system already has:
- R7 source-diverse relationship seeds and registry preflight
- D6 relationship-aware product surface
- Track 2A Kit/Composer handoff
- R6 incident/event packets
- Track 2B city episodes
- asset registry and USD/CER/SEG bridge

So the useful move is not another standalone mobility preflight. The useful move is a bounded R1 domain-pack build that includes its own preflight gate.
