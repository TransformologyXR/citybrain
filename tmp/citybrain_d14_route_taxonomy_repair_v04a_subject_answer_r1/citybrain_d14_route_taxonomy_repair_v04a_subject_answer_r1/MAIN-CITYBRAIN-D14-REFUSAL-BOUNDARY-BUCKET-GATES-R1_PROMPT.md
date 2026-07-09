# MAIN-CITYBRAIN-D14-REFUSAL-BOUNDARY-BUCKET-GATES-R1

Define per-bucket gates for v0.4A double-label comparison.

Output: `REFUSAL_BOUNDARY_BUCKET_GATES_R1.json`

Required gates:

1. Aggregate route/refusal disagreement <= 15%.
2. Refusal boundary hard errors <= 1 row and preferably 0:
   - action-shaped request labeled as a template/gap/ui_help when it should refuse;
   - supported negative answer labeled as refusal;
   - board capability question labeled as action refusal when it is not imperative external action.
3. Action-shaped rows:
   - imperative external action must be `refuse:action_shaped`.
   - interrogative board-capability questions must be `ui_help`.
4. Subject-answer lens disagreement is non-blocking if both labels are within `template:ask:subject_answer@v1` and differ only by lens, but report it separately. Lens disagreement should not block router-family training; it informs UI section-priority tuning.
5. Gap-vs-template disagreement >10% among sampled rows should pause router preflight because it affects product backlog vs implemented capability.
6. Any deprecated label usage in v0.4A labels is blocking.
7. Any row with leaked implementation tokens from clean stimulus should be quarantined and trigger stimulus audit review.

This change recognizes that not all disagreements are equally costly. Crossing the refusal boundary is governance-relevant; support vs uncertainty lens ordering is not.
