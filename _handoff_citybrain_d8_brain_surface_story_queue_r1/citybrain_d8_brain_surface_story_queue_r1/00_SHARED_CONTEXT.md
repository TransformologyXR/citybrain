# CityBrain D8 — Brain Surface Story Queue R1

Purpose: build the first story-queue / brain-surface layer after scenario authoring.

This is NOT a raw-record UI and NOT another inventory. It composes the two validated distinct primary stories into a navigable situation board, with Chicago/Helsinki/governance capabilities woven into story drilldowns where evidence supports them.

Current validated inputs:
- London Wood Lane story: `story:lon:wood_lane_ev_access_review`
  - source records: `TIMS-219173`, `TIMS-210389`, EV asset `87`
  - story query: `story-query:proximity_works_to_access@v1`
  - boundary: proximity is review heuristic, not impact/availability/blockage proof
- NYC cascade story: `story:nyc:cascade:mvc_crash_4463710`
  - source record count: 1
  - affected/context records: 6
  - review options: 5
  - story query: `story-query:incident_to_affected_asset_response_cascade@v1`
  - boundary: candidate tax-lot context is not certified affected-building truth; response-resource context is not dispatched-unit truth; review itinerary is not an action instruction.
- Deep inventory result:
  - total candidates inspected: 27
  - roles: 4 primary_story, 10 capability_cutaway, 6 trust_moment, 6 parked_backlog, 1 data_gap
  - top queue before distinctness filter: Wood Lane, Warwick Avenue, Lancaster Gate, Claps Gate
  - duplicate London proximity stories are not counted as distinct primary stories.
- Scenario authoring R1 validated two counted primary stories and two distinct query versions.

Non-negotiable boundary:
- local/replay/review/query context only
- no production/public API claim
- no autonomous monitoring/alerting
- no dispatch, routing/control, enforcement, official ticket/case, approval, legal/certified finding, or automated action
- execution_state remains `not_executed`
- Track D / human review remains authoritative

Key product rule:
A brain surface is a situation queue + story drilldown + reasoning/trust/cutaway moments.
It is not a wall of source-record cards.
