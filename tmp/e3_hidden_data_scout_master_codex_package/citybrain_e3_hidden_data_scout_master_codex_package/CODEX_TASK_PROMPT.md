# Codex task prompt

You are executing:

```text
MAIN-CITYBRAIN-EPOCH3-HIDDEN-DATA-SCOUT-MASTER-R1
```

Expected status:

```text
PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS
```

## Objective

Scout the repository and all accessible CityBrain artifact roots for hidden, unmaterialized data that could improve Epoch 3 learning or intelligence. Start with the five priority scouts, but also produce a global backlog of additional scout opportunities.

## Required first action

Run a preflight inventory over candidate artifact roots:

```text
outputs/
manifests/
schemas/
fixtures/
tests/
scripts/
docs/
```

Also include any artifact roots referenced by recent Epoch 3 outputs, including:
- entry gate fuel gauge
- Day 1 instrumentation and harness
- Phase 2 live exposure coverage
- L1.R1/R2 outcome/calibration hardening
- pre-closeout convergence
- foundation closeout
- master execution R1
- L2 historical label backfill
- L2.R2 forecast authority preflight
- L2.R2 offline experiment package if present but do not execute model work
```

Do not rely only on file names. Read representative manifests/reports and scan for source refs, source class, dated transition fields, CHECK reports, WatchItems, OutcomeRecords, Briefs, Case artifacts, run envelopes, LLM seat reports, perception/DeepStream/VSS outputs, CER/SEG bridge candidates, and domain-pack outputs.

## Lanes

### Lane A — Hidden Transition Target Scout

Find all possible additional forecast/backtest targets beyond `permit_stall_v0`.

Candidate families include:
- inspection_delay_v0
- violation_resolution_delay_v0
- complaint_escalation_v0
- watch_queue_aging_v0
- roadwork_overrun_v0
- incident_duration_v0
- source_record_staleness_v0
- asset_state_persistence_v0
- service_restoration_time_v0
- backlog_clearance_time_v0

Do not materialize label rows unless separately requested. Publish a candidate target catalog with counts, source refs, temporal-field evidence, censoring complexity, and labelability rating.

### Lane B — CHECK Calibration Fuel Scout

Mine CheckReports, WatchItems, Briefs, decisions, limitations, and OutcomeRecords for pairs where CHECK predicted/flagged:
- candidate_only
- proximity_only
- source_depth_gap
- contradiction
- stale_source
- cannot_claim
- missing_official_source
- source_class_boundary
- detection_confidence_gap

Then identify whether later artifacts resolved the item as confirmed/dismissed/needs_more/held/unresolved. Publish sample depth by check type, source class, family, pack, and city.

### Lane C — L4 Case Memory Fuel Scout

Find prior reviewed or case-like artifacts:
- brief packets
- review options
- Watch queue items
- outcome records
- operator notes/summaries
- held/abstain/needs_source records
- Chicago/NYC/London case-like records
- VSS/cockpit review cards

Measure source_class coverage, outcome lineage coverage, retention/delete readiness, computed-match candidate fields, and whether aggregation floor could be satisfied.

### Lane D — Identity / Graph Evaluation Fuel Scout

Find CER/SEG training/evaluation candidates:
- duplicate entity candidates
- ambiguous building/address/parcel links
- UPRN/address/parcel conflicts
- road-segment rename/bridge candidates
- building footprint overlaps
- candidate affected-asset links
- source-to-canonical bridge candidates
- match/no-match decisions
- graph edge confidence challenges
- temporal edge validity conflicts

Publish candidate positive/negative fixture candidates and "do not merge" examples.

### Lane E — LLM Seat + Perception Usefulness Scout

Find LLM-seat and perception usefulness signals:
- G2 resolver proposal acceptance/fallback/unsafe proposal
- G8/brief writer unsupported-claim or CHECK rejection
- schema validation failure
- latency/cost if present
- human preference vs deterministic rendering
- DeepStream/VSS/Metropolis candidate observations
- frame/clip hashes and timestamps
- review card outcomes
- camera/source registry readiness
- privacy/retention status

Keep perception candidate-only. Do not create production CCTV or official violation claims.

### Track 0 rider — Global hidden-data inventory and backlog

The package must also produce a broad hidden-data backlog covering dimensions not completed in the five initial lanes, including:
- Watch ranking descriptive signals
- domain-pack usefulness data
- simulation/backtest inputs
- synthetic/gold/dirty/challenge/scenario gaps
- operator/fuel-program health
- source-refresh longitudinal gaps
- federation/cross-city comparable artifacts
- data quality/maturity diagnostics
- spatial/Omniverse selection traces
- workflow/review state history

## Non-negotiable boundaries

- No new model training.
- No learned component registry entry.
- No forecast model.
- No ranker.
- No counterfactual learner.
- No case-memory learner.
- No dynamic investigation.
- No cross-city learned transfer.
- No production API, dispatch, enforcement, legal/certified, or official action claim.
- No conversion of single/current snapshots into fake transitions.
- No training eligibility promotion without a later governed materialization package.
