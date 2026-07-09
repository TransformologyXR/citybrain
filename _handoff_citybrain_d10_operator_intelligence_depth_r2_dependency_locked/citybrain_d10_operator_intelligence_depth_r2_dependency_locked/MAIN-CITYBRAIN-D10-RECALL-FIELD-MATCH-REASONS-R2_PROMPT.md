# MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R2

## Purpose
Replace generic RECALL match reasons with field-computed reasons where possible.

## Required matcher contract
Each match result must include:
- source case id
- matched fields
- field values
- match reason text derived from fields
- match strength class
- citations/source records
- what cannot be inferred
- non-match test

## Primary city
Chicago first:
- violations
- inspections
- complaints
- issue type
- date/as-of fields
- location/address fields
- status fields if available

## UI rule
If field-computed match reasons are available, RECALL can be shown as selected-item drawer.
If still generic, RECALL stays limited and not central.

## Output
`RECALL_FIELD_MATCH_REASONS_R2.json`

## Hard fail
Generic prose such as "similar prior case" without matched fields is not enough.
