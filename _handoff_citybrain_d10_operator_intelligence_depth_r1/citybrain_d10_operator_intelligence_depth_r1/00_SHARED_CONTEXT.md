# Shared Context — CityBrain D10 Operator Intelligence Depth R1

## Why this pack exists

Stop the external validation/capture lane for now. The current D9 cockpit has a better operator projection and passed a manual text gate, but the product is still thin. The next useful milestone is product substance: make the cockpit smarter over the available retained city data.

This pack moves CityBrain from a readable cockpit shell toward an operator intelligence surface:

- data-driven review queue, not three showcase cards
- deterministic city-data search, not open-ended model answers
- stronger WATCH query library, not one story/query pattern
- selected-item investigation that explains why something is on the board
- field-computed RECALL match reasons, not generic precedent prose
- DIFF snapshot cadence/status, without claiming live change review
- operator text gate rerun after substance changes

## Current locked state to preserve

- D9 Operator Cockpit UX milestone: `PASS_MAIN_CITYBRAIN_D9_OPERATOR_COCKPIT_UX_MILESTONE_FREEZE_WITH_LIMITATIONS`.
- D9 operator-manual text gate: `PASS_OPERATOR_MANUAL_TEXT_GATE_R1_WITH_MINOR_COPY_LIMITATIONS` per ChatGPT/manual validation.
- ASK/WATCH/BRIEF/CHECK are the live local product modes with limitations.
- RECALL remains partial until match reasons are field-computed.
- DIFF remains unavailable until comparable source-record snapshots/cadence exist.
- Open ASK router remains contract-only. Do not implement a model-in-the-loop router here.
- Perception/VSS/Metropolis and Kit/native Omniverse are outside this lane.

## Durable boundary

CityBrain remains local/LAN/replay/review/query context only.

No production/public API claim. No autonomous monitoring. No operational alerting. No dispatch. No routing/control. No enforcement. No official ticket/case creation. No legal/certified finding. No automated action. No identity/biometric inference. No model-generated factual claim without retained source evidence.

## Product rule

The cockpit must answer city-operator questions:

1. What needs review now?
2. Why is it on the board?
3. What records support it?
4. What is uncertain or missing?
5. What can I ask about it?
6. What can I brief from it?
7. Have we seen similar records before, and why are they similar?
8. What cannot be claimed?

Do not optimize for proving architecture. Optimize for operator usefulness while preserving the inspector/provenance path.
