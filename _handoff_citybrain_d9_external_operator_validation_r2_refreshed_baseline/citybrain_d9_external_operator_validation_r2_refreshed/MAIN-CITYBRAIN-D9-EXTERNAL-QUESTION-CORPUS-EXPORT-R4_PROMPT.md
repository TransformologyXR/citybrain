# MAIN-CITYBRAIN-D9-EXTERNAL-QUESTION-CORPUS-EXPORT-R4

Extract all spontaneous participant questions into:

`inputs/d9_external_operator_questions/operator_question_corpus.jsonl`

Each row:
- raw_question
- session_id
- task_context
- mode_attempted
- user_intent_guess (non-authoritative)
- current_system_result if answered/refused
- suggested_template_candidate if obvious
- should_be_supported_later: true/false
- boundary_sensitive: true/false

This corpus is required input for future Open ASK router implementation. Do not implement the router here.
