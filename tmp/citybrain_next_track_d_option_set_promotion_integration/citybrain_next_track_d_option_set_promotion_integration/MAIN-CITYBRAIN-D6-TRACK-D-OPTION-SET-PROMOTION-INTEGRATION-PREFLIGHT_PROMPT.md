# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-INTEGRATION-PREFLIGHT

Objective:
Define a bounded integration plan that maps decision-support `reviewed_option_set` / `candidate_option` objects into Track D HITL proposal lifecycle without transferring approval authority to the option-set layer.

Use as required upstreams:
- Decision-Support Sprint Certified State and Handover Refresh
- Track D HITL Reviewed Action Milestone Freeze
- Track I Inverse Dynamics Milestone Freeze
- Decision-Support Final Package Review
- Operator Decision-Support Surface R1 if present

Must establish:
- option-to-proposal mapping rules
- eligibility rules for promotion
- human promotion gate
- proposal creation fixture shape
- audit-link requirements
- rejection of automatic promotion
- rejection of execution/dispatch/control/enforcement payloads
- Track D remains authoritative for approval/rejection/modification/request-more-evidence/audit lifecycle

Must not:
- create approved proposals
- execute actions
- mutate Track D
- redefine Track D schema
- redefine `reviewed_option_set`
- create official cases/tickets
- imply dispatch, enforcement, routing/control, legal/certified finding, or automated action

Outputs:
- output root `outputs/main_citybrain_d6_track_d_option_set_promotion_integration_preflight`
- decision JSON
- upstream discovery
- integration contract plan
- option/proposal boundary audit
- no-action/no-mutation/secret/hash audits
