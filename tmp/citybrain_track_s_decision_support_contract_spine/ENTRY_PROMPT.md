# ENTRY PROMPT — Track S Decision-Support Contract Spine

You are Codex continuing CityBrain from the frozen R2 certified-state handover.

Run the Track S package end-to-end in this exact order:

1. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT`
2. `MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-INTERFACE-PREFLIGHT`
3. `MAIN-CITYBRAIN-D6-HERO-CORRIDOR-REVIEWED-ACTION-ENUM-R1`
4. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-GOLDEN-QUALITY-GATE-R1`
5. `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

Use the prompt files in `/prompts/` in sequence.

## Critical execution rules

- Stop on any failing required gate.
- Do not mutate existing upstream outputs.
- Do not stage or commit unless explicitly asked.
- Generated outputs should go under `outputs/`.
- New scripts should go under `scripts/`.
- Preserve unrelated worktree changes.
- Keep all work additive.
- Produce decision JSON, local open index, audits, and hash manifest for every task.

## Track S is contract-only

Do not implement:
- SUMO simulation
- inverse dynamics
- option generators
- similar-case retrieval
- cross-domain cascade
- production APIs
- autonomous monitoring
- dispatch/routing/control/enforcement
- official ticket/case creation
- real-world execution

## Load-bearing architecture rule

The future 9-stage runtime is a governed state machine, not 9 gated LLMs.

Most stages are deterministic code/interfaces.
There is exactly one grounded narration stage: `SYNTHESIZE`.

The motto is:

`code computes, model narrates`

## Required output at the end

After S5, report:
- final status
- output roots
- produced schemas/contracts
- golden quality gate cases
- boundary audit status
- no-mutation audit status
- secret audit status
- hash validation status
- blocking gaps
- non-blocking gaps
- recommended next tasks

Expected closeout status:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS`
