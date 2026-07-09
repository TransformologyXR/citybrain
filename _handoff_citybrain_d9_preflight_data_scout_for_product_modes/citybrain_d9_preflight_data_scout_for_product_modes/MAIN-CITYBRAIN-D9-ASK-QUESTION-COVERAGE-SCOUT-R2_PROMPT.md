# MAIN-CITYBRAIN-D9-ASK-QUESTION-COVERAGE-SCOUT-R2

Create output root:
`outputs/main_citybrain_d9_ask_question_coverage_scout_r2`

Scout ASK mode answerability before implementing the ASK runtime.

Minimum candidate questions to score:
1. What do we know about Wood Lane / Scrubbs Lane?
2. What source records support the Wood Lane story?
3. What is the relationship between the TfL works records and EV asset 87?
4. What is not proven in the Wood Lane story?
5. What do we know about NYC MVC crash 4463710?
6. Which affected/context records are connected to the NYC cascade story?
7. What is not proven in the NYC cascade story?
8. Which review options exist and where does the system stop?
9. What similar precedent/cutaway evidence exists from Chicago?
10. What does Helsinki visual pick prove and not prove?

For each question, classify:
- ANSWER_READY_WITH_CITATIONS
- ANSWER_READY_WITH_LIMITATIONS
- PARTIAL_SOURCE_DEPTH_GAP
- UNSUPPORTED_DO_NOT_ANSWER

Produce:
- ASK_QUESTION_CANDIDATE_SET.json
- ASK_ANSWERABILITY_MATRIX.json
- ASK_REQUIRED_CITATION_MAP.json
- ASK_UNSUPPORTED_QUESTION_LEDGER.json
- ASK_SCOUT_DECISION.json

Acceptance:
- PASS if at least 6 questions are answer-ready or answer-ready-with-limitations.
- PARTIAL if fewer are ready but blockers are clear.
- FAIL if sample answers would require fact invention.
