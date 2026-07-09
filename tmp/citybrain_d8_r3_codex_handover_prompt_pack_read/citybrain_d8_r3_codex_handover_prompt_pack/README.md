# CityBrain D8 R3 Codex Handover Prompt Pack

Purpose: hand off three bounded R3 follow-on tasks to Codex after the D8 follow-on/composition pack passed with limitations.

Tasks included:
1. `HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3`
2. `CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3`
3. `MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3`

Execution guidance:
- These tasks can run in parallel if the repository already contains the referenced R1/R2 output roots.
- Run Helsinki and Chicago first if you want the fastest demo-surface improvement.
- Run VSS only as a gated ingest smoke. Do not claim VSS readiness unless the prompt acceptance criteria are met.
- Preserve all existing D8 boundaries: no large downloads, no prior-output mutation, no production/legal/certified/live/autonomous/VSS-readiness claims.

Recommended next task after these R3 tasks:
`MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1`
