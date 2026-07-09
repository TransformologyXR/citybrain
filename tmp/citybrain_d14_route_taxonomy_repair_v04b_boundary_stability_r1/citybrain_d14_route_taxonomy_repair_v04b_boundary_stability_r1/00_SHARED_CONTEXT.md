# Shared Context — D14 Taxonomy v0.4B

Prior state:
- Synthetic corpus: 150 assembled rows from 6 clean sessions.
- v0.1/v0.2/v0.3 all failed double-label stability.
- v0.4A introduced `template:ask:subject_answer@v1(subject,lens)` and removed direct `what_supports`, `what_is_uncertain`, and `cannot_claim` route labels.
- v0.4A improved lens ambiguity but failed boundary gates:
  - exact disagreement: 14/50 = 28%
  - family disagreement excluding subject-answer lens-only: 13/50 = 26%
  - subject-answer lens-only disagreement: 1/50 = 2% (non-blocking)
  - refusal-boundary hard errors: 5 (max allowed 1)

Diagnosis:
- Subject-answer architecture is working. Keep it.
- Remaining instability is not lens selection; it is boundary interpretation.
- v0.4B must make deterministic first-match rules and canonical examples for the 13 non-lens disagreements.

Durable wall:
- Synthetic rows remain `source_type = synthetic_v0_clean_ai`.
- No real operator validation claim.
- Router training/preflight stays closed until Split/Seal R3 after taxonomy stability.
