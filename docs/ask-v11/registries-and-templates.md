# ASK v1.1 Registries And Templates

P1 adds the registry layer that P2 can compile from. It does not classify
queries, execute retrieval, run CHECK, render prose, or implement future flows.

## Concept-Binding Registry

The Concept-Binding Registry is narrow by design. It maps known question
concepts to claimability boundaries so G2/G7 can distinguish retained facts,
derived context, integrated sources, known external-but-not-ingested concepts,
and unknown concepts.

The v1 seed families are exactly:

```text
charger_asset_availability
access_impact_blockage
live_service_status
planning_legal_determination
certified_geometry
official_case_ticket
source_ownership_who_to_ask
live_external_context
```

Unknown concepts return `unknown_concept` with a triage-oriented claimability
message. Lookups never create new families. Registry growth is demand-led later:
unknown-concept frequency can justify a governed seed update, but runtime lookup
cannot auto-grow the registry.

## Template Registry

The Template Registry is the only source of executable retrieval and answer
contracts for ASK v1.1. Template declarations own:

```text
required_sources
retrieval_plan
derived_features
answer_contract
```

Those fields are registry-owned because G3 is a compiler, not a planner. P2 may
select a registered template from packetized intent and instantiate it with
validated args. P2 may not invent required sources, create a runtime retrieval
plan, add derived features, or alter the answer contract.

Runtime callers may provide only `args` and a route kind. The instantiation
helper rejects attempts to override `required_sources`, `retrieval_plan`,
`derived_features`, or `answer_contract`, and it rejects `raw_query` anywhere in
args or declarations.

The P1 seed templates are fixture-backed contracts for:

```text
board_meta_help@1.0
entity_profile@1.0
subject_answer@1.0
source_record_profile@1.0
patch_queue_query@1.0
external_context_need@1.0
```

Fixture-backed means the contract surface exists for compilation and tests, not
that P1 executes retrieval. P2 can use these records to compile an
`ExecutionContract`; G5 will be responsible for any later template execution.

## Intentional Non-Implementation

P1 intentionally does not implement the G1-G5 execution spine, CHECK runtime,
answer assembly, rendering, data-source calls, or WATCH/BRIEF/DIFF/INCIDENT
logic. Future flows remain outside ASK v1.1 runtime until ASK passes sealed eval.
