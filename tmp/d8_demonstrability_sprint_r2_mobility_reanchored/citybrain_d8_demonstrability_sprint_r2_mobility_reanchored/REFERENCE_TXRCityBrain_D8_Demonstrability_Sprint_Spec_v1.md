# R2 PACKAGE NOTE

The demonstrability acceptance rubric and workstream structure in this v1 spec remain binding. Scenario/spine selection is overridden by `ADDENDUM_R1_D8_SPINE_REANCHOR_AND_MOMENT_REMAP.md`: use the certified Mobility Access corridor as the hero spine; do not build NYC construction substrate in D8 R2.

---

# TXR CityBrain — D8 Demonstrability Sprint (Canonical Spec v1)

Generated: 2026-07-01
Workspace: `C:\Users\hazem\Documents\CityBrain`
Milestone tag: `D8` (demonstrability). *Index is yours to renumber if it collides with your scheme.*
Perspective: canonical sprint/gate spec. Source of truth here; build agents implement runners and report green/red.

---

## 0. One-line charter

Take the already-green, boundary-safe CityBrain fixtures and make **one hero scenario watchable, drivable, and surprising end-to-end**, on the real front ends (web companion + Omniverse Kit), captured as media a person who has never seen it can understand — without building any new capability until the demo is 80% demonstrable.

This sprint changes **no substrate**. It changes what a human can *see*.

---

## 1. The reframed acceptance test (the whole sprint in one sentence)

> A person who has never seen CityBrain watches the hero scenario run **live**, understands it **unaided**, and can **point at the moment it surprised them**.

Every workstream below exists to make that sentence true across at least 10 moments. Gate-pass counts, hash verification, and closeout artifacts are necessary hygiene but are explicitly **not** evidence of demonstrability. The only evidence of demonstrability is a naive viewer who understood and pointed.

---

## 2. Entry gate (precondition — do not start D8 until this is green)

D8 starts only after the current sprint is closed. From your sprint list, "closed" means these are green or explicitly deferred:

- Multi-machine actual deployment rehearsal — green **or** explicitly deferred (it is infrastructure no viewer sees; deferring it does **not** block D8)
- Cross-City Similar-Case Expansion — green or deferred
- Domain-Pack Candidate Selection — green or deferred
- D7 Perception Collateral / Blueprint Pack — green or deferred
- Sprint Integration Readiness Review — green
- Sprint Final Package Review — green
- Sprint Certified-State + Handover Refresh — green

Recommended entry runner: `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SPRINT-PREFLIGHT`
Asserts: prior sprint certified-state present; hero scenario singular and resolvable; web companion + Omniverse Kit build/run locally; `execution_state = not_executed` intact; claim boundary intact.

---

## 3. Definition of "80% demonstrable" (operationalized)

A **moment** is demonstrable when it passes all five checks:

1. **Renders live** — it plays from the running surface, not from a pre-baked screenshot or hand-edited JSON.
2. **Legible unaided** — a naive viewer describes what happened without the operator narrating.
3. **The insight lands** — the viewer can point at the non-obvious thing the system surfaced.
4. **Boundary visible** — review-only is *shown*, not just true: `not_executed` visible, no action taken, authority stays with the human/Track D.
5. **Captured clean** — a recorded clip exists with the claim label and limitations on screen.

**Sprint Definition of Done (all three required):**
- ≥ 80% of the committed moments (≥ 8 of ≥ 10) pass all five checks. Up to 2 may remain `documented_partial` with a one-line reason.
- The integrated surface plays the **full hero scenario** live, end to end, in one sitting.
- Operator-cut and executive-cut walkthroughs are captured, claim-audited, and limitation-honest.

The score lives in one artifact: `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SCOREBOARD` (a JSON + rendered table, one row per moment × five checks).

---

## 4. Goals / Non-goals

**Goals**
- Make one hero scenario demonstrable live on the real front ends.
- Prove intelligence, not just correctness — ≥ 10 surprise moments a naive viewer can point at.
- Produce sendable capture media (operator + executive cuts).
- Harden the front ends under real driving (expect and fix many defects).
- Preserve the review-only positioning under demo pressure — the boundary becomes a visible feature.

**Non-goals (feature freeze — these are the parking lot, not the backlog for this sprint)**
- No new substrate: no new cities, no new domains, no deeper perception stack, no new contracts.
- No security / auth / RBAC / enterprise-security lane (D5 stays deferred).
- No citywide twin expansion; the hero neighbourhood is the whole stage.
- No production, public API, live autonomous monitoring, dispatch, enforcement, or legal-finding paths.
- No conversational persona agents.

Rule: **any scope addition requires a scope removal.** Anything discovered that needs new capability goes to the parking lot (§8), it does not get built this sprint.

---

## 5. Workstream 1 — INTEGRATE (one running surface)

**Intent:** the option set, the 9-stage trace, the promotion candidates, the USD twin, the overlays, and the evidence maps already exist as separate packets. Wire them into **one** surface driven by the hero scenario. Two front ends are in scope and expected to need patching:

- **Web companion** — situation view, evidence/limitations, option set + tradeoffs, runtime-trace panel, Track D promotion panel.
- **Omniverse Kit** — the spatial body: hero neighbourhood twin, graph-to-USD status overlay, replay event/route animation, the affected assets lighting up in context.

The two must present **one truth**: the status the twin shows, the state the trace reports, the option under review, and the promotion candidate are the same review-state, not separate caches that can drift.

**Acceptance (Given/When/Then):**
- Given the hero scenario, When an operator presses play on the web companion, Then the event lands, affected assets light up in the Kit twin, evidence resolves, the option set appears with the do-nothing baseline, the 9-stage trace is watchable stage-by-stage, and a candidate reaches the Track D panel and stops — all from one drive, no manual packet-loading.
- Given any point in that flow, When the operator scrubs the scenario timeline, Then context, overlays, and options update coherently (it reasons over time, not a static snapshot).
- Given the integrated surface, When the promotion panel shows a candidate, Then `execution_state = not_executed` is visible and no approval is created by the panel itself.

Runners:
- `MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-WIRE-R1` (web + Kit + trace panel + promotion panel, one truth)
- `MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-SMOKE-R2` (full live drive + timeline scrub + one-truth negative test)

---

## 6. Workstream 2 — ENGINEER MOMENTS (the ≥10-moment loop)

**What counts as a valid intelligence moment.** A beat where the system surfaces something a sharp human operator would *not* catch quickly, that is (a) non-obvious, (b) cross-connected across data/domains/time, (c) evidence-backed, and (d) boundary-safe. "Here is the event and three options" is a dashboard, not a moment. "The system connected this permit to a dependent asset three hops away and showed why" is a moment.

**The per-moment loop — run this ≥10 times, once per committed moment:**

1. **SELECT** — pick the moment + the exact scenario beat it lives in.
2. **WIRE** — bind the underlying fixture(s) to the integrated surface so the beat renders live.
3. **DRIVE** — run the scenario live to that beat. No pre-baked stills.
4. **TEST** — put it in front of a naive viewer (§3 five checks). Does the insight land? Does the boundary show?
5. **PATCH** — fix the front-end / wiring / labelling defects found. Expect plenty; this is the point.
6. **RE-DRIVE** — confirm the fix and **regression-check every prior green moment** (one surface, so a fix can break a neighbour).
7. **CAPTURE** — record the clip with claim label + limitations on screen.
8. **SCORE** — write the moment's row to the scoreboard.

Loop a moment until it passes all five checks or is consciously marked `documented_partial`.

Runner (parametrised by moment id): `MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-LOOP` with `--moment M01..Mnn`.

**Seed catalogue — commit ≥ 10 of these (all grounded in capabilities you already have as fixtures):**

- **M01 Cross-domain cascade** — a construction/lane event propagates to a dependent infrastructure asset (water/substation) two–three hops away; the twin shows the hidden dependency.
- **M02 Cross-city similar-case** — "this corridor incident resembles a reviewed case in another city; here is what was considered then." (the system has memory across your federated cities)
- **M03 Evidence + honest uncertainty** — operator challenges a claim; the system shows source records, confidence, and flags the one link that is geometry-only (~0.70). It shows what it is *not* sure about.
- **M04 Do-nothing baseline, simulated** — the counterfactual is rendered: "if you do nothing, here is the predicted state," so inaction has a visible cost (anti action-bias).
- **M05 Abstain / no-safe-option** — a beat where the honest answer is "no reviewable-safe option exists — escalate," and the system declines to recommend. (a trust moment)
- **M06 Tradeoff on shared axes** — two options compared on the *same* comparison axes with simulated costs, so a human can actually weigh them.
- **M07 Guardrail catch, live** — an action-shaped object that would cross the boundary (auto-execute / dispatch-shaped) is blocked and logged on screen. The viewer watches it refuse.
- **M08 Track D promotion stop** — an option promotes to a human-review proposal and halts; authority visibly hands to the human; `not_executed` holds.
- **M09 Graph-to-USD status overlay** — a building in the twin changes colour from its graph/compliance state, binding reasoning to the spatial view.
- **M10 Multi-source fusion** — one entity assembled from 3+ siloed sources (permit + parcel + 311 + collision) shown as a single coherent object.
- **M11 Time-scrub reasoning** — scrub the timeline; context/assets/options update, proving reasoning over time.
- **M12 Limitation ledger, in-demo** — the system states on screen what it did *not* check for this scenario (honest scope) — a governance-reviewer moment.
- **M13 Perception candidate → evidence (D7)** — a video/image fixture yields a candidate observation → Event candidate in an EvidenceBundle, explicitly "candidate, not a finding, no identity claim." (the multimodal / NVIDIA-story beat)
- **M14 Persona re-render** — the same EvidenceBundle rendered executive vs operator vs analyst: one truth, many views.

Commit the 10+ in the preflight so the scoreboard has fixed rows. M03, M04, M05, M07, M12 are the ones that most read as *judgment* rather than display — I'd weight the portfolio toward those.

---

## 7. Workstream 3 — CAPTURE (make it sendable)

"Demonstrable" is literal: someone can watch it. Placeholders are replaced with real, reviewed media.

**Acceptance:**
- Operator-cut and executive-cut walkthroughs recorded from the live surface (not slideware).
- Every captured moment shows its claim label and the relevant limitation on screen.
- A claim-boundary audit passes over the final media: no frame implies production, dispatch, enforcement, live autonomous monitoring, or legal finding.
- The same facts as the fixtures — capture introduces **no new claims**.
- A short "what this does not prove" beat is included, on purpose.

Runners:
- `MAIN-CITYBRAIN-D8-CAPTURE-OPERATOR-WALKTHROUGH-R1`
- `MAIN-CITYBRAIN-D8-CAPTURE-EXECUTIVE-WALKTHROUGH-R1`
- `MAIN-CITYBRAIN-D8-CAPTURE-CLAIM-AUDIT` (over all media)

---

## 8. Operating rhythm and defect handling

This is a **test → patch → fix** sprint, not a linear build. Expect many front-end defects; that is the work, not a surprise.

- **Front-end / wiring / labelling defect** → fix in the moment loop now. In scope.
- **One-truth / drift defect** (twin vs trace vs panel disagree) → fix now; it is a demonstrability blocker.
- **Boundary defect** (something looks more live/autonomous than it is) → fix now; highest priority.
- **Capability gap** (the moment needs substrate that does not exist) → **parking lot**, do not build. Either restage the moment on existing substrate or swap it for another seed moment. This is how the feature freeze is enforced in practice.

Parking-lot artifact: `MAIN-CITYBRAIN-D8-PARKING-LOT` (every deferred idea, one line each, so nothing is lost and nothing is built).

---

## 9. Boundary preservation (threaded through every workstream)

Demonstration is exactly where overclaim creeps in — polish tempts you to make it look more live, more autonomous, more certain than it is. The review-only positioning is the project's single biggest asset; protect it under demo pressure:

- Every captured moment passes claim-boundary + no-action + `execution_state = not_executed` + Track D-authority checks.
- The boundary is shown as a **feature**, not hidden: M05, M07, M08, M12 exist so the viewer sees the system decline, refuse, hand off, and admit limits.
- No capture may narrate a fixture as live production data.

---

## 10. Runner sequence (house style)

```
MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SPRINT-PREFLIGHT
MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-WIRE-R1
MAIN-CITYBRAIN-D8-HERO-INTEGRATED-SURFACE-SMOKE-R2
MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-LOOP  (--moment M01 … Mnn, ≥10)
MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SCOREBOARD
MAIN-CITYBRAIN-D8-CAPTURE-OPERATOR-WALKTHROUGH-R1
MAIN-CITYBRAIN-D8-CAPTURE-EXECUTIVE-WALKTHROUGH-R1
MAIN-CITYBRAIN-D8-CAPTURE-CLAIM-AUDIT
MAIN-CITYBRAIN-D8-DEMONSTRABILITY-READINESS-REVIEW
MAIN-CITYBRAIN-D8-DEMONSTRABILITY-FINAL-PACKAGE-REVIEW
MAIN-CITYBRAIN-D8-DEMONSTRABILITY-CERTIFIED-STATE-HANDOFF
```

The moment loop is the long pole and runs many times. Capture trails each moment as it greens (capture continuously, not in a batch at the end).

---

## 11. Success metrics

**Leading (this sprint):**
- Moments demonstrable / committed (target ≥ 80%).
- Naive viewers who understood the scenario unaided (target: several, not zero).
- Naive viewers who pointed at ≥ 1 surprise moment (this is *the* metric).
- Front-end defects found and fixed (a high number is healthy here).

**Lagging (after):**
- External people who have watched the capture and understood it (currently ≈ 0 — this is the number the whole sprint exists to move).
- Demo-to-conversation conversion when the media is shown to a stakeholder.

---

## 12. Exit gate / closeout

Close D8 when the §3 Definition of Done holds. Closeout produces: the scoreboard (≥80% green), the two captured walkthroughs, the claim audit, the parking lot, and a certified-state handoff naming "Hero scenario, demonstrable across N moments on web + Kit" as a single certified capability — so the next sprint (front-end depth, then resumed breadth) builds on a fixed, *demonstrated* baseline rather than a fixture pile.

---

## 13. Open questions (genuinely open — for you)

- Which 10+ of M01–M14 do you commit? (My weighting: include all of M03/M04/M05/M07/M12.)
- How many naive testers, and who? (They must be outside the workspace to count.)
- Capture toolchain for the live surface (screen capture + Kit movie capture) — which, so R1 targets it?
- Is the multi-machine deployment rehearsal deferred for D8, or a hard precondition? (Recommend: deferred — it is invisible to viewers.)
