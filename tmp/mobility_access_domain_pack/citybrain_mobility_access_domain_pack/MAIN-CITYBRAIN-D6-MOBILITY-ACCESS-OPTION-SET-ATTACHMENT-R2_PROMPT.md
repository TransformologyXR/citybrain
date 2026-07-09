# MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-OPTION-SET-ATTACHMENT-R2

Objective:
Attach mobility-access domain context to existing reviewed option-set fixtures as context fields only.

Required:
- attach `mobility_access_refs[]`
- attach `mobility_access_limitations[]`
- attach domain evidence refs
- preserve `execution_state = not_executed`
- preserve mandatory do-nothing baseline
- preserve abstain/no-safe-option state
- preserve Track D as authoritative after promotion

Outputs:
- `MOBILITY_ACCESS_OPTION_SET_ATTACHMENTS.json`
- `MOBILITY_ACCESS_ATTACHMENT_VALIDATION.json`
- `OPTION_SET_SCHEMA_COMPATIBILITY_REPORT.json`
- audits and hash manifest

Pass status:
`PASS_MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_OPTION_SET_ATTACHMENT_R2_WITH_LIMITATIONS`
