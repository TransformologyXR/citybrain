# MAIN-CITYBRAIN-D9-PRODUCT-MODE-CONTRACT-R1

Define the product-mode contract for Ask / Watch / Brief / Check.

## Contract must include

### Ask answer packet
- question_id
- query_text
- answer_summary
- source_refs
- knowns
- unknowns
- cannot_claim
- confidence/limitation block
- execution_state = not_executed

### Watch queue item
- named_query_id
- candidate_id
- candidate_type
- evidence_refs
- review_reason
- false_positive_notes
- human_review_boundary
- no alert / no monitoring claim

### Brief packet
- brief_id
- situation
- evidence
- options
- limitations
- human-stop statement
- source refs
- no-action statement

### Check result
- check_id
- target_ref
- check_type
- status PASS/PARTIAL/BLOCKED
- reason
- source/limitation refs
- remediation suggestion

### Recall cutaway packet
- case_ref
- match_reason
- non-inference note
- source refs
- no instruction/no causality claim

## Required artifacts

- `D9_PRODUCT_MODE_CONTRACT.json`
- `D9_ASK_ANSWER_PACKET_SCHEMA.json`
- `D9_WATCH_QUEUE_ITEM_SCHEMA.json`
- `D9_BRIEF_PACKET_SCHEMA.json`
- `D9_CHECK_RESULT_SCHEMA.json`
- `D9_RECALL_CUTAWAY_SCHEMA.json`
- `D9_PRODUCT_MODE_CONTRACT_R1_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_CONTRACT_R1_WITH_LIMITATIONS`
