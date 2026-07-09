# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04A-SAMPLE-R1

Create the v0.4A blind double-label sample.

Outputs:

- `CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04A_INSTRUCTIONS.md`
- `CORPUS_V0_DOUBLE_LABEL_V04A_SAMPLE_MANIFEST.json`

Sampling requirements:

- At least 25% of relabeled corpus, but no fewer than 50 rows.
- Include all 21 v0.3 disagreement rows as anchors with canonical expected labels hidden from the blind labeler. These rows may be tracked separately in the audit.
- Include fresh hard-shaped top-up rows if available. At least 20 fresh hard-shaped rows should appear in the sample if top-up exists.
- Include unseen rows from each ambiguity bucket:
  - source support vs source record vs claimability
  - EV live/blocked claimability
  - board capability vs external action/help
  - patch queue aggregate/list/filter
  - entity profile vs planning/source boundary
- Do not include Codex labels, expected labels, or route hints in the blind sample.

Instructions file must include only v0.4A taxonomy, the decision tree, allowed labels, and examples. It must not include Codex labels.

The sample should support separate audit categories:

- aggregate disagreement rate
- refusal-boundary disagreement rate
- subject-answer lens disagreement rate
- gap-vs-template disagreement rate
- anchor-row disagreement rate
- fresh-hard-row disagreement rate
