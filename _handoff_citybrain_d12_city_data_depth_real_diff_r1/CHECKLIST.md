# D12 Checklist

- [ ] Verify D11 closeout/freeze exists.
- [ ] Verify D10 DIFF cadence ledger exists and first snapshot was recorded.
- [ ] Enforce consumption rule: no data without a consuming mode artifact.
- [ ] Prioritize London, then Chicago, then NYC; Helsinki/Singapore conditional.
- [ ] Create/refresh source-record snapshot contract.
- [ ] If two comparable snapshots exist, compute source-record/entity-level DIFF.
- [ ] If not, stop DIFF as not ready and continue only consumption-limited data depth.
- [ ] Add/refresh ASK/WATCH/RECALL/CHECK/BRIEF consumers for each landed source.
- [ ] Rerun standing capability regression.
- [ ] Run D12 consolidation/certified-state refresh.
