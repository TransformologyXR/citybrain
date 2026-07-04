# ASK v1.1 R2 Contradiction Patch Plan

## Recommended R2 Action

Proceed with R2 mapping expansion and keep contradiction real-corpus coverage waived.

R2 should not add a real-corpus contradiction case from the current retained corpus because no ready same-claim conflicting-source pair was found.

## R2 Matrix Handling

For the existing contradiction row:

- Keep family: `contradiction`
- Set readiness/disposition: `waived_no_retained_real_pair`
- Preserve sealed fixture coverage reference.
- Do not evaluate it as a real-corpus pass.
- Do not synthesize conflicting evidence.

Suggested R2 note:

```text
Contradiction remains covered by sealed fixture eval. Real retained corpus contradiction coverage is waived for R2 because the scout found no valid same-claim conflicting-source pair. Apparent conflicts were screened out as versioned QA, different commands, different permits, or package lifecycle progression.
```

## If A Retained-Data Addition Is Authorized Later

The smallest plausible addition would be a retained eval-only contradiction assertion artifact that explicitly binds two already-retained artifacts to one claimable field and explains why they should be treated as simultaneous competing assertions rather than version progression.

Potential source pair:

- `outputs/a5d1_operator_query/hero_single_record/hero_parcel_1010607502_grounded_gate_v2.json`
- `outputs/a5d1_operator_query/hero_single_record/hero_parcel_1010607502_grounded_gate_v3.json`

Required normalization before use:

- Define the single claimable field precisely, for example `grounding_gate_status_for_A5_NARRATION_GROUNDED`.
- Explain why v2 and v3 should be treated as competing retained assertions, not old/new versions.
- Include both `narration_path` values.
- Require ASK/CHECK to abstain from choosing PASS or FAIL without a version-specific question.

Until that normalization exists, the pair is not R2-ready.

## Expected CHECK Behavior If A Valid Pair Is Added Later

- Identify contradictory retained assertions.
- Preserve both source references.
- Do not select a winner.
- Emit cannot_claim for the single winning status.
- Render contradiction/abstain language.

## Hard Boundaries

- No G1-G8 runtime change.
- No CHECK rule change.
- No renderer rule change.
- No live retrieval.
- No URL fetch.
- No official action, ticket, dispatch, enforcement, legal, or certified claim.
