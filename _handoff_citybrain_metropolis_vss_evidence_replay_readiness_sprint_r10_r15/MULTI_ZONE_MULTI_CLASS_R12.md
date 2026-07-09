# R12 — Multi-Zone / Multi-Class Candidate Observations

## Goal

Advance beyond one bounded zone and one class where real metadata supports it.

## Zone policy

At least two zones:
- `vehicle_zone_primary`
- `vehicle_zone_context`

Zones may be bounding polygons or frame-relative rectangles.

## Class policy

Use actual DeepStream classes only.

Do not invent a class.

Possible classes depend on the model/config:
- vehicle / car
- person
- bicycle
- road_sign or equivalent if the model exposes it

## Status logic

PASS if:
- at least two zones are evaluated
- at least two classes are observed from real metadata
- observations remain candidate-only

PARTIAL if:
- zones work
- only one class is actually observed

FAIL if:
- synthetic/missing class is claimed as detected
