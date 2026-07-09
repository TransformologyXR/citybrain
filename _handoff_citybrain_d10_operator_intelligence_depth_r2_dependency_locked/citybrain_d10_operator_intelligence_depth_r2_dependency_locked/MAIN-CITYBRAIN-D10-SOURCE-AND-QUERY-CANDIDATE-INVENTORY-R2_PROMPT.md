# MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R2

## Purpose
Inventory retained city sources and identify only candidates that can be consumed by a product mode.

This is not a broad data landing. The D12 consumption rule starts now:
No source/dataset candidate may be promoted unless it has at least one named consumer:
- WATCH query
- ASK template
- RECALL matcher
- CHECK rule
- BRIEF packet use

## Required inventory categories
For each candidate source/record family:
- city
- source family
- current availability
- key fields present
- time/as-of fields present
- entity identifiers
- location fields
- candidate joins
- likely consumer
- reason it matters to operators
- evidence weakness
- whether it should remain parked

## Prioritization
1. London first:
   - operator patch
   - works/access/planning joins
   - address/UPRN improvements if available
   - WATCH and ASK consumers
2. Chicago second:
   - violations/inspections/complaints
   - RECALL field match reasons
3. NYC third:
   - incident/candidate asset/resource context
   - WATCH and CHECK consumers
4. Helsinki only if visual identity helps D13 one-truth seam
5. Singapore only if auth/source blockers are resolved; otherwise parked.

## Output
`SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2.json`

Must include:
- `candidate_count`
- `promoted_candidates`
- `parked_candidates`
- `consumer_required`
- `no_consumer_no_landing_enforced: true`
