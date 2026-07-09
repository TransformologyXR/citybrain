# Shared Context — Source-Backed City Record UI Cutover

Problem discovered by user review: the Web UI is live and renders certified values, but it still displays CityBrain architecture/fixture labels instead of concrete city data. Phrases like "Hero Lon Corridor", "Hero Main Eastbound", "Observation 001", "Similar case 001", and generic option packet names are not enough for a human-facing product.

Root cause: prior prompts allowed "runtime-bundle records" to count as actual records. The runtime bundle contains mostly CityBrain-generated fixture records and refs. A human demo needs official/source-derived city records: city, dataset, external record id, place/address/road/building identifier, time, geometry/location, record fields, source path/URL, license/attribution, and a plain summary derived from those fields.

Boundary unchanged: local/replay/review/query-only; no action, no dispatch, no routing/control, no enforcement, no legal/certified finding; execution_state remains not_executed; Track D/human review authority preserved.

Critical rule: patch the data contract and rendering criteria, not just copy. If no official/source-derived records exist, the correct output is PARTIAL/BLOCKED_FOR_SOURCE_RECORD_DEPTH, not green.
