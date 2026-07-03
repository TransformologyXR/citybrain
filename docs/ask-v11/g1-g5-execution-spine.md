# ASK v1.1 G1-G5 Execution Spine

P2 implements the deterministic front and middle of ASK v1.1:

```text
G1 boundary_screen
G2 intent_and_binding_resolver
G3 route_select_and_compile
G4 argument_resolution
G5 template_execute
```

The spine stops at `EvidencePacket`, `ClarificationPacket`, refusal, gap, or an
honest degraded envelope. It does not run CHECK, assemble answers, render prose,
call LLMs, connect to production sources, or implement future flows.

## G1 Guardrail Only

G1 emits only the P0 `BoundaryResult` vocabulary. Product and board questions
such as export help, alerting capability, or ticket creation capability pass G1
as `clear`; they become answer content later rather than boundary refusals.
Imperative external actions such as alerting, dispatching, routing traffic,
creating official tickets, or issuing violations are `action_shaped` and stop
before G5.

`meta_product_question` is not a G1 class.

## G2 Resolver

G2 is deterministic in P2. It classifies clear queries into the existing
`IntentFamily` values and attaches Concept-Binding Registry findings for known
external concepts. City-subject questions must have an anchor from an explicit
structured ref, `selected_item_ref`, session state, or a recognized fixture
alias. If an anchor is missing, G2 marks the clarification need; it does not
guess.

## G3 Compiler

G3 is a compiler, not a planner. It maps resolved intent families to P1
registered templates and calls the template registry instantiation helper. G3
does not create runtime `required_sources`, `retrieval_plan`, `derived_features`,
or `answer_contract` fields. Missing templates produce a gap route; unsupported
boundary states produce refusal routes.

## G4 Argument Resolution

G4 fills required args only from resolver output, selected item, session state,
explicit extracted refs, or known fixture aliases. If a required value is still
missing, G4 emits one targeted `ClarificationPacket`. It never fabricates an
entity, source record, or queue filter.

## G5 Fixture Execution

G5 is a route-whitelisted fixture executor. It executes only P1 ASK templates
against local P2 fixture records and emits `EvidencePacket` with source refs,
lineage, confidence, gaps, warnings, flags, and `not_executed`.

G5 does not execute live retrieval, production connectors, autonomous actions,
official case/ticket creation, dispatch, control, CHECK, answer assembly, or
rendering.

CHECK, answer assembly, and rendering belong to P3. WATCH, BRIEF, DIFF, and
INCIDENT remain out of runtime scope until ASK v1.1 passes sealed eval.
