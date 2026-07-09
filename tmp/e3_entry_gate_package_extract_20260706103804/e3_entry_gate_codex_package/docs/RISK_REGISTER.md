# E3 Entry Gate Risk Register

| Risk | Severity | Mitigation in this package |
|---|---|---|
| Learning from immature signals | High | R3 thresholds require post-validation-fix, known-propensity, operator-diverse dispositions |
| Selection-bias contamination | High | Day-one exposure logging, propensity metadata, exploration floor, static holdouts |
| Loop numbering drift | High | L3/L4 crosswalk and forbidden identifier test |
| Off-books experiments | High | LearnedComponentRegistry registration required even for offline R3a |
| Forecast model before evaluator | High | L2.R2 blocked until BacktestReport exists |
| Counterfactual overclaim | High | L3 blocked until assumptions, uncertainty, fidelity/surrogate gate, and CHECK coverage exist |
| Memory privacy/retention breach | High | L4 blocked until retention/deletion/privacy/source/outcome lineage enforcement |
| Gate becomes mini-epoch | Medium | Fixed-budget policy; unmeasured items become limitation rows |
| Synthetic data contaminates training | High | Source-class separation and training manifest requirements |
| Arming silently starts work | High | Arming semantics explicitly require ledger row and normal cadence |
