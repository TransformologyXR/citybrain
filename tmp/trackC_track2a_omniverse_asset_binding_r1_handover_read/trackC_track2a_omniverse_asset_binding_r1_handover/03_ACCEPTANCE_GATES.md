# 03 — Acceptance Gates

Target final status:

`PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS`

Required gates:

1. Overlay smoke prerequisite PASS.
2. At least 24 binding records created.
3. At least 16 real BARC/NYC asset binding records.
4. Cross-city DATA_FIRST placeholders labeled, not faked.
5. At least 24 sidecar marker prim references validated.
6. At least 12 Kit/Composer handoff packets created.
7. Evidence refs present where available.
8. Limitation refs present for every binding.
9. Source-ID boundary labels present.
10. Binding confidence and review_state present.
11. No source USD mutation.
12. No app mutation.
13. No-action audit PASS.
14. Claim-boundary audit PASS.
15. No-mutation audit PASS.
16. Secret audit PASS.
17. Hash validation PASS.

Done-when:

Track 2A has a stable bounded asset-binding layer that can be consumed later by D6/Kit or event overlay integration without treating USD/source IDs as certified truth.
