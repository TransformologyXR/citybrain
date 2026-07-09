# D11 Checklist

- [ ] Verify D10 closeout/freeze status is PASS or PASS_WITH_LIMITATIONS.
- [ ] Verify D10 dependency handoff exists and declares DIFF cadence status and Kit probe result.
- [ ] Confirm D10/D11 seam: D11 does not rewrite selected-item content truth.
- [ ] Define local review-state contract with `abstain` first-class.
- [ ] Add local review verbs and log entries without official ID semantics.
- [ ] Add local note/hold/needs-source/reviewed/abstain state.
- [ ] Generate local session summary/export, clearly non-official.
- [ ] Produce external-operator task packet and session templates.
- [ ] If real sessions exist, import/score them and export `operator_question_corpus.jsonl`.
- [ ] If sessions do not exist, close as `READY_FOR_D11_OPERATOR_GATE_PENDING_SESSIONS`.
- [ ] Rerun standing D9 capability regression.
- [ ] Run no-action/no-case/token hygiene audits.
