# ASK v1.1 G6-G8 CHECK, Answer, Render

P3 implements the answer-side contract for ASK v1.1 over P2 fixture evidence:

```text
EvidencePacket -> G6 CheckReport -> G7 AnswerPacket -> G8 RenderedResponse
```

It does not reopen G1-G5, call live or production retrieval, create official
actions, run future flows, or require a live model.

## G6 CHECK

G6 is deterministic evidence sufficiency and claimability validation. It is not
caveat generation. CHECK produces typed findings, verdicts, downgrades,
abstains, coverage limits, contradictions, staleness findings, and binding
findings before any normal answer can exist.

The P3 CHECK engine covers:

```text
source_depth
freshness_staleness
candidate_inferred_link_confidence
proximity_vs_causality
contradiction
coverage_limits
binding_status
```

No-data is a first-class answer state. If retained rows/facts/series are absent,
CHECK emits `insufficient_no_data`, coverage limitations, and a non-claimable
overall state. It does not dress up missing data as weak evidence.

## G7 AnswerPacket

G7 is deterministic. It requires a valid `CheckReport`; without that linkage,
there is no normal `AnswerPacket`. G7 preserves downgrades, abstains,
contradictions, stale flags, coverage notes, binding findings, and
`not_executed`.

`cannot_claim` text is specific: it carries the downgraded claim, abstain reason,
missing source, contradiction, staleness, or retained-data gap. Citations are
created from `EvidencePacket.source_refs` where possible.

## G8 Render

G8 renders from `AnswerPacket` only. P3 uses a deterministic renderer plus an
optional model-proposal callback that receives only the `AnswerPacket`. Every
proposal is passed through a deterministic validator before it can be returned.

The validator blocks attempts to:

```text
turn proximity into causality
turn candidate into confirmed
turn known-external-not-ingested into a live fact
claim legal/certified/final status without support
claim official action, dispatch, alerts, tickets, or violations
invent source names
hide cannot_claim, no-data, coverage, or not_executed
```

If validation fails, G8 returns a degraded rendered response with validation
errors instead of returning the unsafe text. The renderer cannot un-downgrade a
claim already downgraded or abstained by CHECK.

P4 will handle eval sealing and skeleton flow contract tests. WATCH, BRIEF,
DIFF, and INCIDENT remain unimplemented in runtime scope here.
