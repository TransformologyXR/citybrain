# Track S — Decision-Support Contract Spine

This package is a self-contained Codex handover for the next intelligence-track entry point.

Run this package as one Codex thread. It is **sequential**, not parallel.

## Entry point

Start with:

`ENTRY_PROMPT.md`

## Ordered task sequence

1. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT`
2. `MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-INTERFACE-PREFLIGHT`
3. `MAIN-CITYBRAIN-D6-HERO-CORRIDOR-REVIEWED-ACTION-ENUM-R1`
4. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-GOLDEN-QUALITY-GATE-R1`
5. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

## Core rule

This track builds the contract spine only.

It does **not** build Plan Mode, SUMO, inverse dynamics, similar-case retrieval, cross-domain cascade, perception, production APIs, or autonomous action.

## Mandatory semantic rules

- **Option is not Proposal**.
- An `option` is a pre-review candidate inside a `reviewed_option_set`.
- A `proposal` is the Track D HITL object that enters the approval lifecycle after human promotion.
- Track D owns approval/review lifecycle after promotion.
- The option set may mirror/roll up Track D state but must not redefine it.
- D4Y decision-support components are upstream signal/generator inputs, not the new normalized contract.

## Must-have contract features

- mandatory do-nothing baseline option
- first-class abstain/no-safe-option state
- `schema_version` on the set and each option
- explicit comparison axes / tradeoff basis
- generator/simulation provenance and parameters
- `valid_as_of` and `scenario_state_ref`
- golden quality gate that checks decision quality, not only schema

## Boundary

Everything remains local/replay/review/query context only.
