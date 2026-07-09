# Checklist

Hard gates:
- Default UI-ready records must be official/source-derived, not CityBrain fixture refs.
- Each record must include source_url or source_dataset, record_id, geography/address/location if present, timestamp/date if present, plain-language summary, provenance, license/attribution, and limitation label.
- A source record pack with zero source records is PARTIAL, not PASS.
- Do not transform internal fixture IDs into city facts.
- Do not infer missing observation/case details from labels alone.
- No broad full-city download unless explicitly needed and bounded.
