# MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-PACKET-R1

Create a cold-labeler probe packet.

Purpose: after repeated label rounds, Codex and ChatGPT may converge culturally. The taxonomy must be written clearly enough for a fresh labeler to apply it.

Outputs:

- `COLD_LABELER_PROBE_INSTRUCTIONS.md`
- `COLD_LABELER_PROBE_PACKET_R1.jsonl`
- `COLD_LABELER_PROBE_EXPECTED_LABELS_SEALED_HASH.json`

Requirements:

- Select ~20 rows, stratified across hard buckets.
- Include at least:
  - 4 subject-answer support/uncertainty/claimability rows
  - 4 EV live/blocked claimability rows
  - 4 board capability/action rows
  - 4 patch queue/gap rows
  - 2 source-record profile rows
  - 2 entity profile rows
- Give the cold labeler only:
  - v0.4A taxonomy document
  - decision tree
  - row id, persona, selected item context, raw question
- Do not show Codex labels or ChatGPT labels.
- Seal expected labels/hash separately.

The final v0.4A gate should not seal unless the cold-labeler probe is run or explicitly deferred with a limitation. If deferred, record: `COLD_LABELER_PROBE_NOT_DONE` and do not claim taxonomy robustness beyond the Codex/ChatGPT pair.
