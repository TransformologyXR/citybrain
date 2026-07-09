# VSS NARRATION NORMALIZATION RULES — R7

1. Preserve raw VSS response separately.
2. Normalize exactly the fields needed for review.
3. Always set `source_class = model_generated_narrative`.
4. Do not copy VSS object counts as facts.
5. Do not update R2 candidate event metadata from VSS prose.
6. If VSS says something that conflicts with R2 detections, record it as a conflict.
7. If VSS emits forbidden claims, fail the guardrail audit.
8. Human review is always required.
