# ASK v1.1 Real-Corpus Contradiction Source Scout

Package: ASK-V11-REAL-CORPUS-CONTRADICTION-SOURCE-SCOUT
Status: PASS_WITH_LIMITATIONS

## Decision

No ready retained real-corpus contradiction pair was found.

R2 should proceed with a formal contradiction waiver unless a retained-data addition is explicitly authorized before R2. The sealed fixture contradiction coverage remains valid for CHECK behavior, but real-corpus contradiction coverage is not ready.

## Baseline

- Branch: `ask-v11-canonical-implementation-sprint`
- Baseline commit: `3907bc1665e4d02b1410a66146d59a32042d85b3`
- R1 decision: `PASS_ASK_V11_REAL_CORPUS_EVAL_R1_WITH_LIMITATIONS`
- R1 open limitation: contradiction excluded because no true retained conflicting-source pair had been identified.

## Scout Result

- contradiction_candidate_found: no
- screened_candidate_count: 4
- ready_candidate_count: 0
- needs_retained_data_addition_count: 1
- selected_candidate_id: none

## What Was Inspected

- R1 report, summary, failures report, and preflight case matrix.
- ASK-relevant fixture roots under `packages/fixtures`.
- Operator/session inputs under `inputs`.
- ASK real-corpus preflight and R1 outputs.
- A5 operator-query evidence bundles and selected retained output packs.
- A broad exact-ID scan over local JSON under `outputs`, `packages/fixtures`, and `inputs` with a size cap.

## Main Finding

The scan found many apparent status disagreements, but they do not qualify as valid ASK contradiction cases:

- Different permit statuses on one parcel/building belong to different permit jobs.
- Accepted and rejected command statuses belong to different command IDs and action shapes.
- Package PASS/FAIL or accepted/not-accepted values are implementation lifecycle outputs.
- A5 grounding gate v2/v3 has `FAIL` and `PASS`, but the pair evaluates different narration artifacts, so it is not a clean same-claim contradiction without a later retained-data normalization artifact.

## Recommendation

Proceed to `ASK-V11-REAL-CORPUS-EVAL-R2-MAPPING-EXPANSION` with a contradiction waiver:

- Keep sealed fixture contradiction coverage.
- Mark real-corpus contradiction as formally waived for R2.
- Do not invent a contradiction.
- Do not promote lifecycle/version status drift into city-source contradiction evidence.

## Contract Boundaries

- No ASK runtime behavior changed.
- No G1-G8 behavior changed.
- No packet schema changed.
- No registry, CHECK, or render rule changed.
- No future-flow runtime added.
- No live retrieval or URL fetch attempted.
- No official action, ticket, dispatch, enforcement, legal, or certified claim added.
