# Human Fact Cards

Human fact cards are default UI records derived from certified runtime-bundle fields. They must not invent case summaries, observation labels, locations, confidence values, outcomes, or action authority.

Allowed `data_depth_status` values:

- `renderable`: enough certified fields exist for a default human-facing card.
- `partial`: a record exists, but one or more viewer-critical fields are missing.
- `id_only`: only refs/counts exist; show a data-depth gap in the default UI.
- `missing`: the expected record family is absent.

Technical refs may be available in collapsed technical details, but default cards should explain either the actual record or the missing fields.
