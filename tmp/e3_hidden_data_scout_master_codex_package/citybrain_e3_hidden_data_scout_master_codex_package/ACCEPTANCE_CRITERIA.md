# Acceptance criteria

1. Produces `E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json`.
2. Produces an artifact-root inventory with counts and skipped/inaccessible roots.
3. Lane A produces a hidden transition target catalog.
4. Lane B produces a CHECK calibration fuel scout report.
5. Lane C produces an L4 case-memory fuel scout report.
6. Lane D produces an identity/graph eval fuel scout report.
7. Lane E produces an LLM/perception usefulness scout report.
8. Track 0 produces a global hidden-data backlog including dimensions beyond the five initial scouts.
9. Every candidate includes source_refs or a limitation explaining why refs could not be resolved.
10. Every candidate includes source_class and promotion_status.
11. No candidate is marked training-eligible unless it references an already governed materialization artifact.
12. No single/current snapshot is converted into transition history.
13. Perception outputs remain candidate-only and review-only.
14. No new learned component registry entries are created.
15. No model/ranker/forecast/counterfactual/case-memory learner is created.
16. No dynamic investigation or cross-city learned transfer is introduced.
17. Produces a top-priority follow-on package recommendation list.
18. Produces `E3_HIDDEN_DATA_SCOUT_CORPUS_DELTA.json`.
19. Produces no-model/no-fabrication guard report.
20. Produces HASH_MANIFEST and LF/CRLF line-ending report.
21. Focused tests pass.
22. Final status is `PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS` or stricter failure with reason.
