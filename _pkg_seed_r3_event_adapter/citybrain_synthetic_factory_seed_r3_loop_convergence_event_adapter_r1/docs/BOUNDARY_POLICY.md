# Boundary Policy

This task converges the synthetic factory with Event Fabric, but it remains bounded to local replay.

Allowed claims:

- Synthetic factory rows can be emitted in Event Fabric adapter shape.
- Rows can test append/replay/resolve/quarantine/materialize/query behavior.
- Donor/cross-city distributions can seed synthetic Dubai-style behavior.
- The adapter can produce known-truth eval cases and resolver stress fixtures.

Forbidden claims:

- official Dubai truth
- live monitoring
- production live ingestion
- public API
- production frontend
- dispatch, routing, control, enforcement
- legal or certified finding
- human/person-level claims
- LTA/TfL/NYC/Chicago/Barcelona/London records as Dubai facts
- AI diagnostic review as training fuel or founder review fuel

Required source-class labels:

- synthetic_gold
- synthetic_dirty_source
- synthetic_challenge
- synthetic_scenario
- donor_context
- replay_only

Required limitation refs:

- NOT_DUBAI_OFFICIAL_TRUTH
- LOCAL_REPLAY_ONLY
- DONOR_CONTEXT_ONLY
- NO_LIVE_MONITORING
- NO_ACTION_OR_CONTROL
- NO_LEGAL_OR_CERTIFIED_CLAIM
- NO_HUMAN_PERSON_LEVEL_RECORDS
