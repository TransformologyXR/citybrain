# ASK v1.1 Review Checklist

- [ ] Only ASK v1.1 scoped files included.
- [ ] Unrelated dirty worktree files excluded.
- [ ] P0-P4 tests pass.
- [ ] Sealed eval passes.
- [x] Hash manifest verified or status recorded.
- [ ] No live retrieval added.
- [ ] No production API added.
- [ ] No official action/ticket/dispatch added.
- [ ] WATCH/BRIEF/DIFF/INCIDENT are skeleton-only.
- [ ] raw_query rejected downstream.
- [ ] G1 does not include meta_product_question.
- [ ] Board/meta questions route as supported UI/help answers, not boundary refusals.
- [ ] Imperative action requests stop before G5.
- [ ] G3 uses registry templates only.
- [ ] G6 CHECK blocks unsupported claims.
- [ ] G8 cannot un-downgrade.
- [ ] No-data remains first-class.
- [ ] Limitations are explicit.

## Hash Manifest Reconciliation

- [x] Sealed eval report hash drift after rerun has been reconciled:
  - current: 674941af02d3a842cc153eb34510fae641ceda9de55648d0b536bc707d16f281
  - note: rerunning scripts/run_ask_v11_sealed_eval.py after this point requires an intentional manifest refresh.
