# OVERRIDE NOTE — superseded for D8 R2 by Addendum R1

This v1 reference remains included for historical rationale, but its NYC construction spine is not binding for the executable D8 R2 prompt pack. For D8 R2, use `ADDENDUM_R1_D8_SPINE_REANCHOR_AND_MOMENT_REMAP.md`: the certified hero spine is the Mobility Access corridor; NYC construction is parked as post-D8 intelligence work.

---

# TXR CityBrain — D8 Hero Portfolio & Moment-to-Beat Map (Canonical Spec v1)

Generated: 2026-07-01
Workspace: `C:\Users\hazem\Documents\CityBrain`
Companion to: `TXRCityBrain_D8_Demonstrability_Sprint_Spec_v1.md`
Perspective: canonical staging spec. Places each committed moment at a specific beat, in the city whose data actually earns it.

---

## 0. The design decision (one sentence)

Do **not** force one scenario to carry all ten. Run **one thickened NYC hero** as the demo spine (it is the only city with enough co-located data for a long continuous story), and **a few short supporting heroes**, each staging the one or two moments its data is genuinely strongest at — so every moment lands on real data, and every city shows what it is best at.

Each moment is still scored **once**, on the D8 five-check rubric, in its assigned city. A moment staged where the data is thin is a moment that will fail check 3 ("the insight lands") no matter how good the front end is.

---

## PART A — NYC thickened hero: the spine

**Scenario:** *Urban Operations Agent.* One hero neighbourhood (Prospect Heights works — it is the schema's own worked example, BIN 3395389). An active construction permit on a building, a 311 complaint, a road disruption on the adjacent corridor, and an EMS dispatch whose route is affected — all converging on one building/parcel.

**Why NYC carries the spine:** PLUTO (parcels) + DOB-NOW (permits/BIN) + 311 + motor-vehicle collisions + EMS/FDNY dispatch + LL84 energy + the NYC 3D building model are all keyed to the same lots. No other city can bind that many domains to one address with real records.

**The beat map** (T0→T11; each scored moment placed once):

| Beat | What the viewer sees | Moment | Data basis |
|---|---|---|---|
| **T0 — Situation** | Hero neighbourhood loads in the Kit twin; building, parcel, corridor visible. | *(stage-set, not scored)* | NYC 3D model, PLUTO |
| **T1 — Fuse** | A 311 complaint, the active DOB permit, the parcel, and a nearby collision resolve into **one** building object. Siloed sources become one entity. | **M10 Multi-source fusion** | 311 + DOB-NOW + PLUTO + collisions |
| **T2 — Bind to space** | The affected building and adjacent road segment highlight in the twin. *(Connective tissue — the definitive semantic-overlay moment is staged in Helsinki, see Part B.)* | *(connective, not scored here)* | NYC 3D model + graph |
| **T3 — Challenge the evidence** | Operator clicks the collision→road-segment link; the system shows it is **geometry-only, confidence 0.70, "lat/lon only, no link_id."** It shows what it is *not* sure about. | **M03 Evidence + honest uncertainty** | collisions resolved by nearest-geometry (a real low-confidence case in the schema) |
| **T4 — Trace the cascade** | The construction + road disruption propagates to an EMS route delay and a dependent asset; the twin traces the hidden dependency the operator wouldn't see. | **M01 Cross-domain cascade** | DOB + traffic speeds + EMS dispatch + depends_on edges |
| **T5 — Remember** | "This resembles a reviewed case in **Chicago** (violation→inspection)." The system reaches into another city's memory. | **M02 Cross-city similar-case** | NYC incident ↔ **Chicago** violations/inspections (Chicago is the donor, see Part B) |
| **T6 — Cost of doing nothing** | The system simulates the do-nothing counterfactual: predicted congestion + EMS delay worsening. Inaction has a visible cost. | **M04 Do-nothing baseline, simulated** | traffic speeds + EMS ETA model |
| **T7 — Weigh the options** | Two review-only options (e.g. reroute recommendation vs. staging/timing suggestion) compared on the **same axes** with simulated costs. | **M06 Tradeoff on shared axes** | traffic counts (SUMO calibration) + option-set contract |
| **T8 — Refuse the unsafe path** | An action-shaped object (dispatch-shaped / auto-execute) is attempted and **blocked + logged on screen.** The system refuses to cross into dispatch. | **M07 Guardrail catch, live** | HITL guardrail smoke + `not_executed` |
| **T9 — Hand off** | The chosen option promotes to a Track D human-review proposal and **halts.** Authority hands to the human; `execution_state = not_executed` visible. | **M08 Track D promotion stop** | Track D proposal-only spine |
| **T10 — Admit limits** | The system states on-screen what it did **not** check for this scenario (honest scope). | **M12 Limitation ledger, in-demo** | limitation refs / claim boundary |
| **T11 — Re-render** | The same EvidenceBundle re-rendered executive / operator / analyst. One truth, many views. *(Available as a toggle throughout; scored once here.)* | **M14 Persona re-render** | persona rendering policies |

**NYC spine = 9 scored moments** (M10, M03, M01, M02, M04, M06, M07, M08, M12, M14 — M02 is shown here but its donor case lives in Chicago). This is a coherent one-sitting story: *situation → fuse → show uncertainty → trace cascade → recall a precedent → simulate inaction → compare options → refuse the unsafe action → hand to a human → state limits.*

**Thickening work required (Workstream-1, no new substrate):** ensure T4's cascade edge and T6's do-nothing sim are wired to the live surface, and that T8's guardrail object is actually attempted (not just described) so the refusal is watchable. Everything else exists as fixtures.

---

## PART B — Supporting heroes: one signature moment each

These are **short, self-contained cutaways** (30–90s each), not full scenarios. Each stages the moment NYC cannot do as well, on the city whose open data is the strongest real donor for it.

| City | Scenario | Signature moment(s) | Why this city (real data basis) | Tier |
|---|---|---|---|---|
| **Singapore** | *Real-Time Eyes* | **M13 Perception candidate→evidence** | **LTA Traffic Images API** is a real camera-style feed — the strongest open donor for the "eyes." A frame → candidate observation → Event candidate in an EvidenceBundle, labelled "candidate, not a finding, no identity claim." | **1 (commit)** |
| **Helsinki** | *Semantic 3D Twin* | **M09 Graph-to-USD status overlay** (definitive form) | Helsinki's 3D city model **is** a published digital twin with a *semantic* city model + reality mesh — the cleanest "every visible object resolves to a graph entity" showcase. | **1 (commit)** |
| **Chicago** | *Sensor-Fusion Brain* | **M02 donor** (the retrieved reviewed case) + optional M13 variant | Chicago has real building **violations + inspections + 311** (the precedent NYC recalls at T5) and the **Array of Things** + 277-sensor air network (an alternative "eyes" if Singapore images aren't demo-ready). | **1 (commit as M02 source; M13 as fallback)** |
| **London** | *Resilient City Command* | **M01 environmental cascade** (second instance) | TfL road disruptions + **London Fire Brigade** mobilisation + **LAQN** air quality + smart-meter energy = a cross-domain cascade in a different domain mix. UK-relevant (NVIDIA). | 2 (recommended) |
| **Melbourne** | *City Over Time* | **M11 Time-scrub reasoning** (definitive form) | Real **hourly pedestrian counts since 2009** + parking-bay sensors = an actual time series to scrub; context/options update as you move through time. | 2 (recommended) |
| **Dubai** | *DM–DLD Compliance* | **M05 Abstain / no-safe-option** + property-fusion (M10 variant) | DLD land→building→unit→project→developer→transaction is a beautiful fusion graph and ties to the TXR narrative — **but** high-frequency traffic/camera/utility data is sparse, which makes it the *honest* home for "insufficient evidence → escalate." | 3 (stretch; ties to TXR story) |

**M05 (abstain) placement note:** abstain is most convincing where data is genuinely thin. Dubai's known sparsity is a feature here — the system honestly declining on a Dubai sub-question is a stronger trust moment than a manufactured abstain inside data-rich NYC.

---

## PART C — How it stitches, scores, and what to commit

**Stitch:** NYC is the through-line the viewer follows start to finish. The supporting heroes are cutaways introduced by one line each ("here's the same reasoning where the city has a live camera / a semantic twin / years of history"). The operator-cut walkthrough runs NYC end-to-end and drops in the committed cutaways; the executive-cut is the NYC spine plus one or two cutaways.

**Score:** every moment is still one row on `MAIN-CITYBRAIN-D8-DEMONSTRABILITY-SCOREBOARD`, five checks each, regardless of which city hosts it. City assignment changes *where* a moment is staged, not *how* it's scored.

**Committed portfolio (clears ≥10 honestly):**
- NYC spine: **9** (M10, M03, M01, M04, M06, M07, M08, M12, M14)
- + Singapore **M13**, Helsinki **M09**, Chicago **M02**-donor = **12 scored moments across 4 cities.**
- Tier-2/3 (London M01-env, Melbourne M11, Dubai M05) add breadth *if* data readiness allows — pure upside, not required for the 80% bar.

**Why this beats a single 10-moment NYC marathon:** it removes the two moments NYC fakes worst (a real camera, a semantic twin), it turns your multi-city data into a *visible* asset instead of an unused inventory, and it makes M02 (cross-city memory) literally true rather than staged — the retrieval reaches into a second city's real records.

---

## Open questions (for you)

- **Commit the Tier-1 four (NYC + Singapore + Helsinki + Chicago)?** That's the honest ≥10. Which Tier-2/3 do you want to attempt as upside?
- **Singapore vs. Chicago for the "eyes" (M13):** which camera/sensor donor is more demo-ready right now — Singapore LTA traffic images, or Chicago Array of Things? Pick one to build, keep the other as fallback.
- **Helsinki twin:** do you already have the Helsinki semantic model staged in Kit, or does M09 need a separate ingest? (If ingest, it may slip to Tier-2.)
- **One hero neighbourhood per supporting city, or reuse a single block each?** Recommend one tight block per city to keep each cutaway legible.

---

*Next dr-aftable on request: the NYC scenario-thickening script (the exact fixtures/edges to wire for T4 cascade, T6 do-nothing sim, and T8 guardrail attempt), or the Singapore/Helsinki cutaway shot-lists.*
