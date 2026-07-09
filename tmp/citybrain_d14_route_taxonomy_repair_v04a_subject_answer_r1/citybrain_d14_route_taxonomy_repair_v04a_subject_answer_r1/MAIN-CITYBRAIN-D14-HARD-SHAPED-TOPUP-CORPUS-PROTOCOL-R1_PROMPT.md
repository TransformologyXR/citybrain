# MAIN-CITYBRAIN-D14-HARD-SHAPED-TOPUP-CORPUS-PROTOCOL-R1

Create a targeted clean-session top-up protocol for hard-shaped rows.

Purpose: avoid denominator gaming. The next double-label sample must include fresh unseen rows shaped like the ambiguity buckets that caused v0.3 to fail, not just the easier remainder.

Output:

- `HARD_SHAPED_TOPUP_CORPUS_PROTOCOL.md`
- `HARD_SHAPED_TOPUP_CLEAN_SESSION_PROMPT.md`
- optional `inputs/d14_synthetic_operator_questions/hard_shaped_topup/README.md`

Protocol requirements:

- Use fresh clean sessions, not this project thread and not Codex.
- Use same frozen `DEFAULT_VISIBLE_TEXT.txt` stimulus and SHA-256 as prior synthetic corpus where possible.
- Do not show the taxonomy, templates, route labels, implementation details, or this contract to the clean model.
- Ask for 60 rows total across at least 2 clean runs / 2 model families if feasible.
- Distribution targets:
  - 15 source-support vs source-record phrasings
  - 15 EV live/blocked/availability/claimability phrasings
  - 10 board capability vs external action phrasings
  - 10 patch queue count/list/filter/compare phrasings
  - 5 entity profile vs planning/source boundary phrasings
  - 5 noisy follow-up/pronoun rows across the above
- Preserve `source_type = synthetic_v0_clean_ai_hard_topup` or `synthetic_v0_clean_ai` with `topup_batch = hard_v04a`.
- Leave all labels null.

Important: If the human cannot run top-up sessions immediately, v0.4A may still relabel the original 150 rows, but the closeout must say whether fresh hard-shaped rows were included. Do not claim the hard-row stability gate if no fresh top-up rows exist.
