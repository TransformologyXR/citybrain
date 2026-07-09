# MAIN-CITYBRAIN-D8-CHICAGO-SIMILAR-CASE-NORMALIZATION-R2

Goal: normalize Chicago rows into viewer-ready similar case cards.

Each case:
{
  "similar_case_id": "...",
  "city": "Chicago",
  "case_title": "...",
  "source_record_ids": [...],
  "address_or_area": "...",
  "what_happened": "...",
  "why_it_matches_mobility_access": "...",
  "what_was_reviewed": "...",
  "outcome_or_known_limit": "...",
  "not_an_instruction": true,
  "limitations": [...]
}

If source data only supports generic violations/requests, say so. Do not create outcomes not in source data.
