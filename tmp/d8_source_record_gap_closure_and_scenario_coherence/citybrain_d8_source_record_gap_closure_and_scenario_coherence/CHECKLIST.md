# Checklist

Run in order unless a stage explicitly returns PARTIAL and instructs to stop.

1. Source-record gap closure preflight.
2. M13 D7 media/candidate-observation source-record pack.
3. M07 guardrail refusal review-log source-record pack.
4. M08 human-review stop source-record pack.
5. London mobility corridor coherence review.
6. Web source-record gap-closure UI integration.
7. City-fact viewer readiness review.
8. Closeout.
9. Milestone freeze.

Hard stop:
- If a stage lacks actual record fields, return PARTIAL with exact missing fields.
- Do not invent source frame/time/location/summary/outcome/refusal log/proposal-stop evidence.
- Do not count internal packet IDs as default-view city facts.
