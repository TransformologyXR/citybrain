# MAIN-CITYBRAIN-D12-CONSUMPTION-RULE-LEDGER-R1

Create the consumption ledger. No source can land without a consumer in the same sprint.

Consumer types:
- WATCH query
- ASK template
- RECALL matcher
- CHECK rule
- BRIEF section/use

Ledger row fields:
- source_family
- city
- candidate_dataset_or_file
- intended consumer
- consumer artifact id/version
- operator question or queue item it improves
- source-depth risk
- status: `accepted_for_landing`, `parked_no_consumer`, `blocked_source_unavailable`

Any `parked_no_consumer` source is not ingested into the product runtime.

Deliverables:
- `D12_CONSUMPTION_RULE_LEDGER.json`
- `PARKED_DATA_NO_CONSUMER.md`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
