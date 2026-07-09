# MAIN-CITYBRAIN-D6-TRACK-D-OPTION-SET-PROMOTION-BRIDGE-R1

Objective:
Produce deterministic bridge fixtures that show how eligible candidate options can be prepared for human promotion into Track D proposal objects, while keeping all proposals unapproved and unexecuted.

Inputs:
- preflight output
- Track D proposal schema/lifecycle outputs
- reviewed option-set examples from Track S/I/Decision-Support sprint

Requirements:
- generate promotion candidate fixtures only
- preserve `option_id`, `option_set_id`, evidence refs, simulation refs, similar-case refs, cascade refs, limitation refs, and audit refs
- assign `proposal_ref = null` unless representing a pending/unapproved fixture explicitly marked not authoritative
- all fixtures must have `execution_state = not_executed`
- include do-nothing and abstain/no-safe-option cases as non-promotion or escalation cases
- include negative cases for blocked action types

Outputs:
- bridge fixture JSON/JSONL
- mapping matrix
- validation report
- claim/no-action/no-mutation/secret/hash audits
