# R13 — Human Review UI Packet

## Goal

Prepare a stable frontend-ready packet.

## Packet sections

- candidate card summary
- media preview refs
- frame/clip refs
- DeepStream metadata summary
- VSS narration sidecar summary
- knowns
- unknowns
- cannot-claim
- source-class labels
- audit labels
- allowed review states

## Allowed review states

```text
needs_review
hold_for_source
abstain_insufficient_evidence
reviewed_candidate_only
export_review_packet
```

## Forbidden review states

```text
create_ticket
dispatch
enforce
confirm_violation
identify_person
```
