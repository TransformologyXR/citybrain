# MAIN-CITYBRAIN-D9-ASK-CITED-ANSWER-RUNTIME-R3

Implement a local, deterministic Ask answer runtime over the product-mode bundle.

## Scope

No external LLM call required. Use deterministic templates over source/evidence/limitation data.

## Required seed questions

- What does CityBrain know about Wood Lane / Scrubbs Lane and which records support it?
- What is known about MVC crash 4463710 and the candidate affected/context records?
- What is uncertain or unsupported in this story/packet?
- What cannot be claimed?
- What source records support this answer?

## Acceptance

Every answer must include:
- summary
- citations/source refs
- knowns
- unknowns
- cannot_claim
- limitations
- not_executed / human-review boundary where relevant

## Required artifacts

- `D9_ASK_ANSWER_LIBRARY.json`
- `D9_ASK_SAMPLE_ANSWERS.json`
- `D9_ASK_ANSWERABILITY_VALIDATION.json`
- `D9_ASK_CITED_ANSWER_RUNTIME_R3_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_ASK_CITED_ANSWER_RUNTIME_R3_WITH_LIMITATIONS`
