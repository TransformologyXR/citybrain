# ASK v1.1 Real-Corpus Eval R2 Limitations And Waivers

## Formal Contradiction Waiver

No valid retained same-claim contradiction pair was found during the contradiction-source scout. Real-corpus contradiction coverage is waived for R2. Contradiction remains covered by sealed fixture eval and should be added to real-corpus coverage only when a genuine retained conflict pair appears.

## Why This Is Acceptable For R2

Contradiction handling is safety-critical, but the absence of a clean retained contradiction pair is not itself a runtime failure. The scout screened apparent conflicts and found they were versioned QA, different command IDs, different permit jobs, or package lifecycle progression rather than same entity / same claim / same field / same timeframe conflicts.

## Remaining Limitations

- R2 real-corpus contradiction coverage is waived.
- Current real-corpus mapping is eval-only and does not expand runtime G5 beyond the sealed fixture scope.
- Embedded source URLs remain retained citations only; they were not fetched.
- The R2 artifacts are generated outputs and should be staged intentionally in the later commit package.
- Local drift in `outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json` was observed as unrelated generated-output drift and was not restored or committed in this package.

## Future Admission Rule For Real-Corpus Contradiction

A future real-corpus contradiction case should be admitted only when retained local artifacts show:

- same entity/ref,
- same claimable field,
- same as-of window or snapshot,
- incompatible retained assertions,
- no reliance on live retrieval or new external fetching.

When added, ASK/CHECK should preserve both sides, set contradiction/downgrade behavior, avoid choosing a winner, and prevent renderer un-downgrade.
