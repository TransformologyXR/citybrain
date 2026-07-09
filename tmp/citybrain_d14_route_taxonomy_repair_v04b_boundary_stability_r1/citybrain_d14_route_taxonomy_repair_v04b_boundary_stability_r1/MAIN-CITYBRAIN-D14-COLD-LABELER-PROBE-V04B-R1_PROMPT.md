# MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-V04B-R1

Prepare a cold-labeler probe packet, but do not run it unless the user explicitly chooses to.

Purpose:
A cold labeler should be able to label a small sample using only the written v0.4B taxonomy. This tests whether the rules live in the document, not just in Codex/ChatGPT shared history.

Output:
- `COLD_LABELER_PROBE_V04B_PACKET.jsonl` with 20 rows.
- `COLD_LABELER_PROBE_V04B_INSTRUCTIONS.md` containing only the v0.4B decision tree and output schema.

Do not include Codex labels or ChatGPT labels.

This is a secondary stability check. It does not replace the main double-label gate.
