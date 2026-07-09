# Checklist — D14 Staged Router Schema Repair R1

## Preflight
- [ ] Confirm prior v0.4B result is recorded as failed for flat route taxonomy.
- [ ] Confirm no Split/Seal R3 has run.
- [ ] Confirm router preflight/training remains unopened.
- [ ] Confirm real operator validation is not claimed.
- [ ] Confirm D13 live seam state is recorded separately and not mixed into D14 route work.

## Staged schema contract
- [ ] Define Stage A boundary vocabulary and composition rule.
- [ ] Define Stage B intent-family vocabulary, including `meta_product_question`.
- [ ] Define Stage C route targets inside each family.
- [ ] Define Stage D subject-answer lens vocabulary.
- [ ] Define Stage E selected-item context flag.
- [ ] Define per-stage error pricing and gates.
- [ ] Define on-policy vs all-stage reporting.

## Migration
- [ ] Mechanically migrate all 150 v0.4B-labeled rows to staged schema.
- [ ] Preserve original row provenance and synthetic source labels.
- [ ] Flag ambiguous migration rows instead of silently adjudicating.
- [ ] Produce migration report and predicted-hard sample.

## Top-up protocol
- [ ] Create clean-session targeted top-up prompt/protocol.
- [ ] Target boundary-shaped and product-meta phrasings.
- [ ] Do not run top-up unless clean sessions are available.
- [ ] If top-up not present, record limitation clearly.

## Double-label sample
- [ ] Build staged blind sample with existing hard rows + ambiguous migration rows + fresh top-up rows if available.
- [ ] Include no Codex labels or route hints.
- [ ] Export independent-label instructions.
- [ ] Stop for independent labels.

## Gates after independent labels
- [ ] Stage A disagreement <= 5%, with refusal-boundary hard errors <= 1 and ideally 0.
- [ ] Stage B disagreement <= 15%.
- [ ] Stage C disagreement <= 20%.
- [ ] Stage D lens disagreement <= 25% and non-blocking unless it changes output family.
- [ ] Stage E context-flag disagreement <= 15%.
- [ ] Full-path exact agreement reported as informational only.
- [ ] Cold-labeler probe prepared before Split/Seal.

## Do not do
- [ ] Do not adjudicate failed v0.4B into pass.
- [ ] Do not open router preflight.
- [ ] Do not train router.
- [ ] Do not seal before staged schema passes.
- [ ] Do not count synthetic rows as real operator validation.
