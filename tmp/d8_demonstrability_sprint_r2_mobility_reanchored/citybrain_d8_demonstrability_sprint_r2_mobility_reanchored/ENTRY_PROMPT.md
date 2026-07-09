You are continuing CityBrain after the product/domain/perception post-review handover and infra/data deployment closeout have validated green.

Use the included reference docs as the D8 source of truth, with Addendum R1 taking precedence for scenario/spine selection:
- `REFERENCE_TXRCityBrain_D8_Demonstrability_Sprint_Spec_v1.md`
- `REFERENCE_TXRCityBrain_D8_Hero_Portfolio_and_Moment_Beat_Map_v1.md` (historical/reference only where it conflicts with Addendum R1)
- `ADDENDUM_R1_D8_SPINE_REANCHOR_AND_MOMENT_REMAP.md` (**binding override**)

Run the D8 Demonstrability Sprint in order.

Critical entry gate:
- Do not start D8 unless the current product/domain/perception post-review certified-state/handover refresh is green, and the infra/data deployment milestone freeze is green or explicitly deferred.
- The hero spine must equal the certified tip scenario: **Mobility Access corridor**.
- NYC construction is parked as post-D8 work, not built in this sprint.
- If either closeout is missing, or if the runner tries to build a non-certified scenario as the spine, fail safely with `WAITING_FOR_D8_ENTRY_GATE` or `FAIL_D8_SPINE_NOT_CERTIFIED_TIP` and list missing/invalid upstreams.

D8 objective:
Make CityBrain demonstrable, not merely validated. A naive viewer should be able to watch the certified hero spine run live, understand it unaided, and point at a surprising moment.

Boundary:
- Local/replay/review/query context only.
- No production/public API claim.
- No live autonomous monitoring.
- No alerts.
- No dispatch.
- No routing/control.
- No enforcement.
- No official ticket/case creation.
- No legal/certified finding.
- No automated action.
- `execution_state = not_executed` remains visible.
- Track D remains authoritative after human promotion.

Run this sequence:
1. `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SPRINT-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-HERO-PORTFOLIO-AND-MOMENT-BEAT-MAP-LOCK-R1`
3. `MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-WIRE-R1`
4. `MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-SMOKE-R2`
5. `MAIN-CITYBRAIN-D8-HERO-SPINE-MOMENT-WIRING-R1`
6. `MAIN-CITYBRAIN-D8-SUPPORTING-HERO-CUTAWAY-WIRING-R1`
7. `MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-LOOP-AND-SCOREBOARD-R1`
8. `MAIN-CITYBRAIN-D8-CAPTURE-OPERATOR-WALKTHROUGH-R1`
9. `MAIN-CITYBRAIN-D8-CAPTURE-EXECUTIVE-WALKTHROUGH-R1`
10. `MAIN-CITYBRAIN-D8-CAPTURE-CLAIM-AUDIT-R2`
11. `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-READINESS-REVIEW`
12. `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-FINAL-PACKAGE-REVIEW`
13. `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-CERTIFIED-STATE-HANDOFF`

Do not stage or commit unless explicitly asked.
