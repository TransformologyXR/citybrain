Below is the chronological summary of what was built or closed for **CityBrain in this thread**. Where the task itself did not include an internal timestamp, I date it as **7 July 2026**, the date of this conversation.

## Chronological build summary

| Date           | Build / task                                                    | What was built                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Result                                                                                |
| -------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **7 Jul 2026** | `DATA-GAP-LEDGER-AND-PRIORITY-MATRIX`                           | Built the D8 “treasure map”: 26 source entries classified, 10 gaps ranked, source-access status captured, next data landing recommendation produced. It corrected Singapore traffic image status: `data.gov.sg` traffic image probe was `403`; LTA DataMall remained API-key gated.                                                                                                                                                                                                                                                 | `PASS`                                                                                |
| **7 Jul 2026** | `MAIN-CITYBRAIN-D8-PARALLEL-DATA-READINESS-SCOUTS`              | Ran the full D8 parallel readiness scout sequence: gap ledger, Helsinki readiness, Metropolis/VSS readiness, camera/video inventory, mobility option set, temporal/simulation readiness, and Web/Kit demo bundle readiness. It established the D8 lane map: Helsinki as the strongest data lane; VSS as gated; mobility M04/M05 ready for bounded render; Web/Kit ready with limitations.                                                                                                                                           | `PASS_MAIN_CITYBRAIN_D8_PARALLEL_DATA_READINESS_SCOUTS_WITH_LIMITATIONS`              |
| **7 Jul 2026** | `D4-HELSINKI-KALASATAMA-CONTEXT-DATA-LANDING-R1`                | Landed the first Helsinki/Kalasatama context package. This introduced a serious semantic CityGML identity spine: 2,980 buildings, 13,437 roof surfaces, 34,260 wall surfaces, 2,923 ground surfaces; plus HSL GTFS candidates, energy workbooks, planning metadata, and Smart Kalasatama reports.                                                                                                                                                                                                                                   | `PASS_D4_HELSINKI_KALASATAMA_CONTEXT_DATA_LANDING_R1_WITH_LIMITATIONS`                |
| **7 Jul 2026** | `D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1`            | Consumed the Helsinki package into CityBrain-ready artifacts: 2,980/2,980 CityGML building identity rows, 2,980 CER candidate rows, 2,980 USD/CER sidecar candidate rows, HSL candidate context, energy workbook join classification, and a visual mesh boundary note. The 3D mesh was explicitly kept as `VISUAL_BACKDROP_ONLY`.                                                                                                                                                                                                   | `PASS_D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_WITH_LIMITATIONS`            |
| **7 Jul 2026** | D8 parallel prompt pack generation                              | I created the prompt pack for the next D8 lanes: Mobility abstain patch, VSS licensed corpus acquisition, Web+Kit bundle consumption smoke, Helsinki USD sidecar alignment smoke, and Chicago similar-case bounded enrichment. This matched the broader architecture idea that Omniverse/Kit becomes more useful when it consumes canonical/evidence packets rather than static visual data. The supporting docs frame asset binding as canonical IDs, evidence refs, graph/runtime refs, limitation refs, and USDA marker layers.  | Prompt pack created                                                                   |
| **7 Jul 2026** | `CITYBRAIN-D8-PARALLEL-PROMPT-PACK`                             | Ran the full D8 parallel prompt pack. Built/closed five bounded lanes: M04/M05 mobility abstain semantics, VSS acquisition readiness package with gates closed, Web+Kit smoke over 12 moments, Helsinki 20 USD/CER sidecar packets plus USDA handoff layer, and Chicago 15-row similar-case memory packet.                                                                                                                                                                                                                          | `PASS_CITYBRAIN_D8_PARALLEL_PROMPT_PACK_WITH_LIMITATIONS`                             |
| **7 Jul 2026** | D8 follow-on/composition prompt pack                            | I prepared the next pack for three follow-ons plus closeout/composition: VSS licensed corpus sample acquisition R2, Helsinki Kit object-pick manual alignment R2, Chicago reviewed matching R2, D8 parallel pack composition closeout R1, and D8 demonstrable surface integration R1.                                                                                                                                                                                                                                               | Prompt pack created                                                                   |
| **7 Jul 2026** | `CITYBRAIN-D8-FOLLOWON-AND-COMPOSITION-PROMPT-PACK`             | Ran the follow-on/composition pack. Built: VSS R2 readiness with sample gate still closed, Helsinki R2 with 20 manual object-pick alignment packets and USDA sidecar layer, Chicago R2 with 15 reviewed cases and 45 bounded matches, composition closeout inventory across lanes, and a 7-step local demo route.                                                                                                                                                                                                                   | `PASS_CITYBRAIN_D8_FOLLOWON_AND_COMPOSITION_PROMPT_PACK_WITH_LIMITATIONS`             |
| **7 Jul 2026** | R3 Codex handover prompt pack                                   | I prepared the R3 handover pack for Helsinki manual review capture, Chicago demo query smoke, and VSS sample ingest smoke, plus optional R3 closeout.                                                                                                                                                                                                                                                                                                                                                                               | Prompt pack created                                                                   |
| **7 Jul 2026** | `CITYBRAIN-D8-R3-FOLLOWON-PROMPT-PACK`                          | Ran the R3 follow-ons. Built: 20 Helsinki object-pick packets captured, still `pending_review`; Chicago demo query smoke with 15 reviewed cases, 45 bounded matches, 5 demo query fixtures, and 1 clean abstain for citywide trend query; VSS sample ingest smoke with 9 candidates evaluated, 0 eligible, gate still closed.                                                                                                                                                                                                       | `PASS_CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_WITH_LIMITATIONS`                          |
| **7 Jul 2026** | D8 final demo capture/handoff prompt pack                       | I prepared the final D8 Codex handover prompt pack for `MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1`.                                                                                                                                                                                                                                                                                                                                                                                                             | Prompt pack created                                                                   |
| **7 Jul 2026** | `MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1` | Froze D8 into a certified local-demo handoff. Locked state: Helsinki 20 pending pick packets; Chicago 15 reviewed cases, 45 bounded matches, 1 abstain; VSS sample ingest gate closed; 7-step final demo route; operator script; certified-state handoff; hash manifest; clean audits. ZIP SHA256: `10640e8ce63745585596634f2eae352b1874fa2a99c88873d787c819613a4189`.                                                                                                                                                              | `PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS` |
| **7 Jul 2026** | D9 demo polish/review prompt pack                               | I prepared the D9 prompt pack for demo polish/review loop R1 and optional human-review session capture R2.                                                                                                                                                                                                                                                                                                                                                                                                                          | Prompt pack created                                                                   |
| **7 Jul 2026** | `MAIN-CITYBRAIN-D9-DEMO-POLISH-AND-REVIEW-LOOP-R1`              | Built the polished D9 demo review layer: polished demo route, polished operator script, executive one-pager, review index HTML, scorecard, and derivative review artifacts. Scorecard: 6 PASS, 2 PASS_WITH_LIMITATIONS, 1 NEEDS_REVIEW. Remaining gap: screenshots/video not captured due to environment limitation.                                                                                                                                                                                                                | `PASS_MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_WITH_LIMITATIONS`              |
| **7 Jul 2026** | D9 human review session capture R2 prompt pack                  | I prepared the R2 prompt pack to explicitly capture the screenshot/video/reviewer gap instead of pretending it was done.                                                                                                                                                                                                                                                                                                                                                                                                            | Prompt pack created                                                                   |
| **7 Jul 2026** | `MAIN-CITYBRAIN-D9-HUMAN-REVIEW-SESSION-CAPTURE-R2`             | Built the human-review capture ledger package: 7 demo steps represented, review ledger, review capture index, review notes, capture gap register. It correctly recorded screenshots = 0, videos = 0, reviewer identity not invented, and review status still `NEEDS_HUMAN_REVIEW`.                                                                                                                                                                                                                                                  | `PASS_MAIN_CITYBRAIN_D9_HUMAN_REVIEW_SESSION_CAPTURE_R2_WITH_LIMITATIONS`             |
| **7 Jul 2026** | D9 manual capture R3 prompt pack                                | I prepared the R3 prompt pack for manual screenshot/video capture and optional public demo readiness closeout R4.                                                                                                                                                                                                                                                                                                                                                                                                                   | Prompt pack created                                                                   |

## What this thread actually produced

By the end of this thread, **D8 moved from data-gap scouting to a certified bounded local demo handoff**, and **D9 moved into polish/review capture**.

The concrete product surface now includes:

* A ranked data-gap/source-readiness picture.
* A Helsinki/Kalasatama semantic visual-object lane.
* A CityGML → CER → USD/CER sidecar path with 2,980 building candidates.
* A bounded mobility baseline with explicit abstain semantics for M04/M05.
* A VSS acquisition/readiness lane that correctly remains closed.
* A Web+Kit demo consumption smoke.
* A Chicago “city remembers” similar-case lane with reviewed cases and demo query fixtures.
* A 7-step D8 local demo route.
* A certified D8 handoff package with hash manifest and clean audits.
* A D9 polished route, operator script, executive one-pager, and review index.
* A D9 human review capture package that honestly records the remaining screenshot/video gap.

## Main architectural meaning

This thread strengthened CityBrain as a **review-only city intelligence cockpit**, not a production control system. That matches the product loop documented elsewhere: CityBrain should run source records/events/spatial selections through identity resolution, graph/context retrieval, evidence assembly, CHECK/claimability validation, human-facing modes such as WATCH/ASK/BRIEF/RECALL/DIFF/SPATIAL, and then human review state. 

The thread also reinforced the split between:

* **identity and evidence**: Helsinki CityGML/CER/USD sidecars;
* **memory/recall**: Chicago similar-case packet;
* **demo surface**: Web+Kit and D8 route;
* **governance**: abstain semantics, VSS gates closed, no legal/live/autonomous/production claims.

This is consistent with the wider Track 2A / Omniverse logic: asset binding should carry canonical entity IDs, evidence refs, graph/runtime refs, limitation refs, and review state into Kit/Composer rather than claiming a full citywide twin. 

## Key boundaries preserved throughout

Every completed package kept the same boundaries:

* No production readiness claim.
* No legal/certified operational claim.
* No live operational claim.
* No autonomous action, dispatch, enforcement, or control claim.
* No VSS runtime/readiness claim.
* No invented reviewer identity.
* No invented screenshots or videos.
* No prior-output mutation.
* No large-download escalation in the bounded lanes.

## Current final state

As of **7 July 2026**, the thread ends here:

```text
D8 = certified bounded local-demo handoff complete with limitations
D9 R1 = polished review/demo layer complete with limitations
D9 R2 = human review capture ledger complete with limitations
Remaining gap = manual screenshot/video capture and real human review
Next task = MAIN-CITYBRAIN-D9-MANUAL-SCREENSHOT-VIDEO-CAPTURE-R3
```

The strongest one-line summary:

**This thread turned CityBrain D8 from a data-readiness question into a bounded, certified, review-only demo surface, then started D9 by polishing the demo and cleanly registering the remaining human capture gap.**
