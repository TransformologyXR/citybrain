# MAIN-CITYBRAIN-D8-D7-MEDIA-OBSERVATION-SOURCE-RECORD-PACK-R1

Goal: turn M13 from "candidate observation refs are ID-only" into viewer-ready observation source records, if the data exists.

Search bounded inputs:
- D7 perception candidate observation milestone/freeze outputs.
- D7 collateral/media review outputs.
- any local demo media manifests, candidate observation JSON/JSONL, frame/clip metadata, source URLs, timestamps, labels, locations, review state.
- Do not download external video in this stage.

A valid M13 source record requires at minimum:
- observation_id
- source_media_ref or source_frame/clip placeholder with provenance
- timestamp or explicit `timestamp_missing`
- location/camera/source context or explicit `location_missing`
- candidate_label
- plain_language_observation_summary
- review_status = candidate_only / human_review_required
- not_a_finding = true
- limitations
- evidence refs

If the record cannot meet this minimum, produce PARTIAL and keep the blocker.

Produce:
- `D7_MEDIA_OBSERVATION_SOURCE_RECORD_PACK_R1_DECISION.json`
- `d7_media_observation_source_records.json`
- `D7_OBSERVATION_DATA_DEPTH_GAPS.json`
- `NO_FACT_INVENTION_AUDIT.json`
- `HASH_MANIFEST.json`

Do not re-label six bare refs as observations. Bare refs remain technical details only.
