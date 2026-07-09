# MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R2

## Purpose
Define deterministic search over retained city records for operator investigation.

This is not Open ASK. No model router implementation.

## Search contract
Support deterministic query families over retained data:
- exact ID lookup
- known alias/name lookup
- selected-item context lookup
- nearby/linked source records already in retained graph
- source-record search by city/source family
- fielded lookup over retained identifiers
- knowns/unknowns/cannot-claim assembly from source facts

## Required behavior
- Return cited records only.
- Return no-answer/refusal when unsupported.
- Show nearest supported searches/templates when available.
- Do not generate facts from model.
- Do not search the open internet.
- Do not imply completeness beyond retained corpus.

## Output
`CITY_DATA_SEARCH_CONTRACT_R2.json`

Include:
- supported search types
- input schemas
- output schema
- citation requirements
- refusal reasons
- examples for London/NYC/Chicago
- negative tests
