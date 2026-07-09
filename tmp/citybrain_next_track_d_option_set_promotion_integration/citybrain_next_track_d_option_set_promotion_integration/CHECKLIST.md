# Checklist — Track D — Option-Set Promotion Integration

Before running:
- [ ] Confirm next-sprint selection review has selected this lane, or user explicitly instructed execution.
- [ ] Confirm latest certified state exists: `PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS`.
- [ ] Confirm generated outputs remain additive under `outputs/`.
- [ ] Do not mutate prior frozen output roots.
- [ ] Preserve existing unrelated working-tree changes.

During execution:
- [ ] Produce decision JSON per task.
- [ ] Produce `LOCAL_OPEN_INDEX.md`.
- [ ] Produce validation report.
- [ ] Produce claim-boundary audit.
- [ ] Produce no-action/no-mutation/secret audits.
- [ ] Produce hash manifest.
- [ ] Keep boundary language visible in README and decision files.

End condition:
- [ ] Final closeout or R1 decision is PASS with limitations.
- [ ] Blocking gaps are zero, or task fails explicitly.
- [ ] Non-blocking gaps are disclosed.

