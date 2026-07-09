# ADDENDUM R1 — D8 Spine Re-anchor & Moment Remap

Generated: 2026-07-01
Applies to: `citybrain_d8_demonstrability_sprint` prompt pack
Status: **advisory patch — apply before running runner #2 (BEAT-MAP-LOCK).** Does not change the D8 boundary or objective.

---

## 1. What was checked, and the verdict

Inspected the full pack (19 files) against the current certified tip
(`main_citybrain_d6_mobility_d7_trace_domainpack_post_review_certified_state_and_handover_refresh`).

- Boundary: **clean.** Review-only, `not_executed`, Track D authority, no-dispatch/enforcement/legal are carried faithfully in every prompt.
- Sequence & artifacts: **sound.** Preflight gate, scoreboard, capture, readiness/final/handoff all present and well-formed.
- **One finding, blocking for runner #2 onward:** the pack hard-codes a **NYC construction hero** that is **not the certified substrate.** Building it would be new substrate, which the pack's own preflight forbids.

Everything else in the pack stands. This addendum changes *which scenario the spine points at* and *how moments bind to real fixtures* — nothing else.

---

## 2. The finding (substrate mismatch)

The pack's spine assumes NYC construction-compliance data:
- `BEAT-MAP-LOCK-R1`: "Required default portfolio: **NYC thickened spine** carrying M10, M03, M01, M04, M06, M07, M08, M12, M14."
- `NYC-SPINE-MOMENT-WIRING-R1`: beats built on NYC permits + 311 + collisions + EMS dispatch (M10 four-source fusion, M03 collision-geometry-0.70 uncertainty, M01 building→EMS cascade).

The certified tip is a **Mobility Access hero corridor**, not NYC construction:

```text
Mobility Access entity refs: 7
Relationship families: 5
Reviewed option sets: 3   candidate options: 7   option-set attachments: 3
D7 candidate observations: 6   human-review packets: 6
Operator trace stages: 9
Eligible Track D panel packets: 3   approved proposals: 0   negative promotion tests: 9/9 PASS
Cross-city similar cases: 4   similar-case attachments: 2
execution_state: not_executed
```

The NYC construction scenario's specific data (permit+parcel+311+collision fusion, a collision→road-segment low-confidence link, a building→EMS cascade) is **not present** in this substrate. Wiring those beats would either fail at capture (a moment staged on data that isn't there fails scoreboard check 3, "insight lands") or force a build agent to fabricate NYC substrate — violating "no new substrate is authorized" and your stated D8 intent to *iron out the current spine*, not grow a new one.

**Conclusion:** re-anchor the D8 spine on the Mobility Access corridor that is actually certified. Keep NYC construction as a **post-D8 "more intelligence" target** in the parking lot.

---

## 3. Reassurance: re-anchoring does NOT cost the 80% bar

The mobility substrate already carries most of the moments — including the "judgment" ones that make it read as a brain. You do not need the NYC hero to clear ≥8/10.

| Moment | Status on certified mobility substrate | Real data basis |
|---|---|---|
| **M02** cross-city memory | **REAL** | 4 similar cases, 2 attachments |
| **M13** perception → evidence | **REAL** | 6 D7 candidate observations + 6 human-review packets |
| **M07** live guardrail refusal | **REAL** | 9/9 negative promotion tests |
| **M08** Track D promotion stop | **REAL** | 3 eligible packets, 0 approved, authority preserved |
| **M12** limitation ledger | **REAL** | 3 non-blocking gaps + limitations list |
| **9-stage trace** (spine connective) | **REAL** | operator trace-panel milestone green, 9 stages |
| **M06** tradeoff on shared axes | **REAL if axes present** | 3 option sets / 7 options — verify shared comparison axes |
| **M14** persona re-render | **VERIFY** | needs persona rendering policies as a surface — not confirmed in certified facts |
| **M10** multi-source fusion | **RESTAGE** | fuse the 7 entity refs / 5 relationship families (mobility), not NYC 4-source |
| **M03** honest uncertainty | **RESTAGE** | surface a low-confidence link among the 5 relationship families |
| **M01** cross-domain cascade | **RESTAGE** | mobility-corridor cascade across the 5 families, not building→EMS |
| **M04** do-nothing baseline | **PARTIAL / DEFER** | depends on the `do_nothing_baseline` field being populated in the 3 option sets (see §4) |
| **M05** abstain (if committed) | **PARTIAL / DEFER** | depends on `option_set_outcome = no_safe_reviewed_option` being present (see §4) |
| **M09** Helsinki semantic twin | **DEFER / FALLBACK** | no Helsinki data — pack already handles as fallback |

Count: **6 REAL + 3 restageable (on real mobility data) = 9 demonstrable** without building any new substrate. That clears ≥8/10. M04/M05/M09/M14 are upside, not requirements.

---

## 4. The M04/M05 dependency flag (decide consciously)

M04 (do-nothing baseline) and M05 (abstain) were designed against the `reviewed_option_set` contract's `do_nothing_baseline_option_id` and `option_set_outcome` fields. Those fields came from a **contract draft that post-dates these 3 certified option sets.** Before committing M04/M05:

- **Check** whether the 3 certified option sets already carry a baseline option and the abstain outcome enum.
- If **yes** → M04/M05 are REAL, promote them.
- If **no** → populating those fields is arguably new substrate. Either (a) mark M04/M05 `documented_partial` for D8 and schedule the contract backfill as the first *post-D8* intelligence task, or (b) make a conscious, logged exception to the freeze for the baseline field only (it is the single most valuable anti-action-bias moment). Do not let a build agent silently invent baselines to make the moment render.

---

## 5. Prompt patches (small, precise)

Apply these edits to the pack. NYC is concentrated in two files; the rest are one-line touch-ups.

1. **`ENTRY_PROMPT.md` step 5** — rename
   `MAIN-CITYBRAIN-D8-NYC-SPINE-MOMENT-WIRING-R1` →
   `MAIN-CITYBRAIN-D8-HERO-SPINE-MOMENT-WIRING-R1` (substrate-neutral).

2. **`MAIN-CITYBRAIN-D8-NYC-SPINE-MOMENT-WIRING-R1_PROMPT.md`** — retitle to `HERO-SPINE`, and replace the "Required beats" block so each beat binds to a **certified Mobility Access fixture ref** per the §3 table. Keep the three "critical thickening" items (visible cascade, simulated do-nothing, live guardrail refusal) — they are substrate-neutral and still the highest-value work.

3. **`MAIN-CITYBRAIN-D8-HERO-PORTFOLIO-AND-MOMENT-BEAT-MAP-LOCK-R1_PROMPT.md`** — change "Required default portfolio: NYC thickened spine…" to:
   > Required default portfolio: **the certified hero spine (currently the Mobility Access corridor)** carrying M02, M13, M07, M08, M12 and the 9-stage trace as REAL; M10, M03, M01 restaged on mobility data; M06 if shared axes present; M04, M05 only if the option-set contract fields are populated (see Addendum R1 §4).
   Add a validation line: **every committed moment's `data_basis` must resolve to a discoverable ref in the certified tip; fail-safe any moment whose basis is not found.** (This turns "thin-data moment" into a hard gate, not a capture-time surprise.)

4. **`00_SHARED_CONTEXT.md`** — change "NYC thickened hero as the long spine" to "the certified hero spine (Mobility Access corridor) as the long spine; NYC construction hero is a **post-D8** target in the parking lot."

5. **Capture prompts (operator/exec)** — replace the single "NYC" reference with "the certified hero spine," so the walkthrough narrates the mobility corridor.

6. **`PREFLIGHT`** — add one assertion to `D8_SCOPE_LOCK.json`: *"Hero spine = certified tip scenario. NYC construction hero is parked, not built."*

Unchanged: the whole sequence, the boundary, the scoreboard five-check rubric, the supporting-hero fallback logic, readiness/final/handoff. Singapore/Helsinki/Chicago cutaways remain optional enrichment — note that M13 is now *also* satisfiable directly from the certified D7 observations, so the Singapore cutaway becomes upside rather than the only source of the "eyes."

---

## 6. Net

The pack is good and the boundary is intact; the only thing wrong is that the substrate moved to Mobility Access while the reference docs still pointed at NYC construction. Re-anchor the spine on what is certified, bind every moment to a real ref, park NYC construction for the post-D8 intelligence phase, and D8 still clears ≥8/10 on real data. This is exactly the class of issue D8 exists to surface — it just surfaced at spec-review time instead of at capture time, which is the cheapest place to catch it.
