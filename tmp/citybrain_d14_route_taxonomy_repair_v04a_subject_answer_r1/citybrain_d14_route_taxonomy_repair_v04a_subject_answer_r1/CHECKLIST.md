# Checklist — D14 Route Taxonomy Repair v0.4A

- [ ] Confirm v0.4A supersedes the earlier v0.4 package.
- [ ] Do not run Split/Seal R3 before all v0.4A gates pass.
- [ ] Do not open router training/preflight before split/seal.
- [ ] Create explicit product-architecture decision for `ask:subject_answer@v1(subject,lens)`.
- [ ] Relabel the full 150-row synthetic corpus under the reduced route taxonomy.
- [ ] Preserve all row provenance and `source_type = synthetic_v0_clean_ai`.
- [ ] Preserve real-operator validation block.
- [ ] Generate fresh hard-shaped clean-session top-up rows focused on remaining ambiguity buckets.
- [ ] Label/merge top-up rows under v0.4A without using them to claim real validation.
- [ ] Build blind double-label sample containing prior hard rows plus fresh hard-shaped rows.
- [ ] Add per-bucket gates, especially near-zero refusal-boundary disagreement.
- [ ] Run cold-labeler probe with a fresh labeler using only the v0.4A taxonomy document and ~20 rows.
- [ ] Stop for independent labels before adjudication.
- [ ] If aggregate disagreement >15%, stop.
- [ ] If refusal-boundary disagreement >0 or near-zero threshold, stop.
- [ ] If cold-labeler probe fails, stop.
- [ ] Only after all gates pass, run Split/Seal R3.
