# Claude Independent AI Diagnostic Review Prompt — CityBrain Story Arc R1

You are acting as an independent **AI diagnostic reviewer** for a bounded CityBrain story artifact.

Do **not** treat this as founder input, operator validation, training fuel, client readiness, product readiness, live monitoring, forecast validation, official workflow validation, dispatch/control/enforcement, legal/certified review, or source-truth mutation.

## Local artifact to inspect

Use the local folder if available:

```text
C:\Users\hazem\Documents\CityBrain\outputs\MAIN-CITYBRAIN-CROSS-DOMAIN-STORY-ARC-EVAL-EXPANSION-R1
```

Prioritize these files:

```text
CROSS_DOMAIN_STORY_ARC_DECISION.json
CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json
CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json
CROSS_FAMILY_CAUSAL_LINK_LEDGER.json
STORY_ARC_REVIEW_PACKET_360.md
STORY_ARC_REVIEW_PACKET_360.json
STORY_ARC_EVAL_COVERAGE_SCORECARD.json
STORY_ARC_EVAL_EXPANSION_CASES.jsonl
STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl
STORY_ARC_FOUNDER_DIAGNOSTIC_CARD_CANDIDATES.json
BOUNDARY_NO_ACTION_AUDIT.json
NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json
NO_FOUNDER_SESSION_FUEL_GUARD.json
NO_FORECAST_ACTION_GUARD.json
NO_SOURCE_TRUTH_MUTATION_GUARD.json
NO_STANDALONE_FIXTURE_REGRESSION_GUARD.json
```

## Known run summary to verify, not blindly trust

```text
Status: PASS_MAIN_CITYBRAIN_CROSS_DOMAIN_STORY_ARC_EVAL_EXPANSION_R1_WITH_LIMITATIONS
Story arc id: cross-domain-story-arc-r1-construction-permit-access-compliance-asset-cascade
New eval cases: 120
Existing eval cases: 48
Combined eval cases: 168
Shared canonical entity gate: True
Product review ready: False
Client ready: False
Next recommendation: GO_FOR_AI_DIAGNOSTIC_STORY_REVIEW
```

## Your review questions

Answer these directly:

1. Does the packet read as one coherent cross-domain city story, or as stitched events?
2. Is the shared canonical entity evidence understandable and traceable?
3. Is the corridor/asset context honestly separated from same-site identity?
4. Does CHECK prevent overclaiming, especially around causality, weak spatial match, stale/unknown freshness, duplicate ambiguity, and quarantine?
5. Is mobility truly native-packet-backed in this story, or does it still rely on derived backfill?
6. Are the simulation labels conservative enough: donor-distribution-aligned fixture, not city-calibrated, not forecast, no ForecastPacket?
7. Are the 120 new eval cases grounded in the truth manifest, or inflated?
8. Are the negative/challenge cases useful for catching overclaiming?
9. Are the proposed founder diagnostic cards now useful for product judgment, or still evidence-debugging?
10. Should this proceed to founder diagnostic review, stay in AI diagnostic repair, or be parked?

## Required structured output

Use this exact structure:

```text
AI_DIAGNOSTIC_REVIEW_STATUS:
  PASS_WITH_LIMITATIONS / NEEDS_REPAIR / NO_GO

FOUNDER_DIAGNOSTIC_REVIEW_RECOMMENDATION:
  GO_WITH_LIMITATIONS / WAIT_FOR_REPAIR / NO_GO

FOUNDER_PRODUCT_REVIEW_RECOMMENDATION:
  NO_GO / CANDIDATE_AFTER_MORE_EVIDENCE / GO_WITH_LIMITATIONS

RATINGS_1_TO_5:
  story_coherence:
  evidence_traceability:
  cross_family_entity_resolution_clarity:
  check_boundary_clarity:
  simulation_context_honesty:
  eval_expansion_usefulness:
  founder_diagnostic_usefulness:
  product_review_readiness:

TOP_STRENGTHS:
  - ...

TOP_LIMITATIONS:
  - ...

BLOCKERS:
  - ...

OVERCLAIMING_OR_BOUNDARY_RISKS:
  - ...

REPAIR_ACTIONS_BEFORE_FOUNDER_DIAGNOSTIC:
  - ...

FINAL_RECOMMENDATION:
  ...
```

Keep the boundary strict: this review is `ai_diagnostic_review`, `operator_fuel=false`, `training_eligible=false`, `founder_session_result=false`, `external_operator_validation=false`.

