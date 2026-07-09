# MAIN-CITYBRAIN-D8-MOBILITY-TEMPORAL-AND-SIMULATION-DATA-SCOUT

Goal: identify what data is missing to make Mobility Access do-nothing baseline, shared-axis tradeoffs, and time-scrub reasoning real.

Inspect:
- road network / SUMO context used by Mobility Access
- traffic speed/count sources
- transit/GTFS or public transport feeds if already landed
- incident/route/ETA fixtures
- historical/current-state rows suitable for timeline scrub

Outputs:
- MOBILITY_TEMPORAL_SOURCE_INVENTORY.json
- SIMULATION_BASELINE_REQUIREMENTS.md
- SHARED_AXIS_TRADEOFF_DATA_REQUIREMENTS.json
- TIME_SCRUB_DATA_GAP_REPORT.md
- SOURCE_ACQUISITION_PLAN.json
- LIMITATION_LEDGER.md
- HASH_MANIFEST.json

Boundary:
Simulation is context-only. No certified traffic model, routing/control, dispatch, or real-world operational recommendation.
