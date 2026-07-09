# Checklist — Operator Decision-Support Surface R1

Run only after Cross-Domain Cascade is green.

Acceptance checklist:
- Required upstream discovery includes Track S, Track B, Track R, Track I, Decision-Support handover, and Cross-Domain Cascade closeout/freeze.
- Surface consumes existing `reviewed_option_set` packets and does not redefine them.
- Surface shows do-nothing baseline, candidate interventions, abstain/no-safe-option, comparison axes, SUMO refs, similar-case refs, cascade refs, and Track D promotion boundary.
- Surface separates option display from Track D proposal lifecycle.
- Surface preserves execution_state=`not_executed`.
- Surface includes operator-facing explanation of limitations.
- Surface produces web/operator packet fixtures and a local-open index.
- Claim-boundary audit PASS.
- No-action audit PASS.
- No-mutation audit PASS.
- Secret audit PASS.
- Hash manifest PASS.
- Blocking gaps = 0.
