# MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-PACKET-R1

## Goal
Prepare a cold-labeler probe packet to test whether the staged taxonomy lives in the written document, not just in Codex/ChatGPT shared culture.

## Probe design
- 20 rows.
- Include hard buckets and normal rows.
- Use staged schema instructions only.
- No prior labels, no v0.4 history, no implementation notes beyond the staged taxonomy document.
- Labeler may be a fresh AI session or a person not involved in prior taxonomy iterations.

## Output expected later
`CORPUS_V0_COLD_LABELER_STAGED_LABELS.jsonl`

## Gate
Cold-labeler probe should not replace the main double-label gate, but it must be reviewed before Split/Seal.

## Outputs
- `COLD_LABELER_STAGED_PROBE_PACKET.jsonl`
- `COLD_LABELER_STAGED_PROBE_INSTRUCTIONS.md`
- `COLD_LABELER_STAGED_PROBE_MANIFEST.json`

## Status
`PASS_D14_COLD_LABELER_PROBE_PACKET_READY`
