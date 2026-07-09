# TASK PROMPT — MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3

## Goal

Run a gated ingest smoke for a VSS-style licensed corpus sample only if a valid local sample exists.

This task must preserve the VSS gates. If no audited licensed corpus sample is present, emit a closed-gate result and do not fabricate, download, scrape, or substitute media.

## Upstream context

Use the most recent VSS R2 output, expected around:

- `outputs/main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/`
- `outputs/main_citybrain_d8_vss_licensed_corpus_acquisition_r1/`
- D8 parallel/follow-on closeout outputs that reference VSS

Known upstream facts:
- VSS R2 passed with limitations.
- Sample gate remained `CLOSED`.
- VSS gates remain closed unless a real audited licensed sample exists.
- Singapore data.gov traffic images had 403 and LTA Traffic Images v2 remains AccountKey-gated.
- Do not use unlicensed public traffic media as a substitute.

Discover actual roots from closeout/decision JSONs if path names differ.

## Licensed sample requirements

A sample is ingest-eligible only if all of these exist locally:

1. Media file or clip file.
2. License/provenance record explicitly allowing project use.
3. Camera metadata:
   - camera_id or source_camera_ref
   - location or bounded site reference, if available
   - timestamp or capture interval, if available
   - source system/source owner
4. Privacy/sensitivity label.
5. Expected-output oracle or review label file, even if minimal.
6. Hash/provenance record for the media.

If any requirement is missing, do not ingest media. Produce a closed-gate decision.

## Required behavior if sample is missing or incomplete

1. Load VSS R2 readiness/acquisition records.
2. Check for local sample candidates.
3. Classify missing requirements.
4. Keep `sample_ingest_gate = CLOSED`.
5. Create an operator checklist for what is needed next.
6. Do not ingest media.
7. Do not claim VSS readiness.

Expected status:
`PASS_WITH_LIMITATIONS`

## Required behavior if sample is complete

1. Copy or reference the local sample without mutating the source.
2. Verify media hash.
3. Validate license/provenance file.
4. Validate camera metadata.
5. Validate privacy/sensitivity label.
6. Validate expected-output oracle/review labels.
7. Create an ingest manifest.
8. Run only a structural ingest smoke:
   - file readable
   - metadata readable
   - oracle readable
   - manifest links resolve
   - no model inference unless a local approved test command already exists
9. Keep VSS runtime readiness claim closed unless real VSS runtime acceptance criteria also exist.

Expected status:
`PASS_WITH_LIMITATIONS` or `PASS` only if all ingest smoke criteria are complete and no readiness overclaim is made.

## Required outputs

Output root:

`outputs/main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3/`

Files:

- `MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json`
- `VSS_SAMPLE_ELIGIBILITY_CHECK.json`
- `VSS_SAMPLE_INGEST_MANIFEST.json`
- `VSS_MISSING_REQUIREMENTS_CHECKLIST.md`
- `VSS_LICENSE_AND_PRIVACY_AUDIT.json`
- `VSS_CAMERA_METADATA_AUDIT.json`
- `VSS_ORACLE_AUDIT.json`
- `VSS_RUNTIME_READINESS_BOUNDARY.md`
- `REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json`
- `JSON_PARSE_AUDIT.json`
- `SECRET_SCAN_AUDIT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
- `HASH_MANIFEST.sha256`

## Decision JSON schema

Include at least:

```json
{
  "task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3",
  "status": "PASS_WITH_LIMITATIONS",
  "upstream_roots": [],
  "sample_candidates_found": 0,
  "eligible_samples": 0,
  "sample_ingest_gate": "CLOSED",
  "runtime_readiness_gate": "CLOSED",
  "licensed_corpus_claim": false,
  "vss_runtime_readiness_claim": false,
  "missing_requirements": [],
  "ingest_manifest_created": false,
  "audits": {},
  "limitations": [],
  "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1"
}
```

## Acceptance criteria

Pass with limitations if:
- VSS R2 records load cleanly.
- Sample eligibility is evaluated.
- Gate remains closed when required metadata/license/oracle is missing.
- No media is downloaded, scraped, fabricated, or substituted.
- No VSS readiness claim is made.
- All audits pass.

Pass only if:
- A complete local licensed sample exists.
- License, camera metadata, privacy label, oracle, and hashes all validate.
- Structural ingest smoke succeeds.
- The output still avoids overclaiming runtime readiness.

Fail if:
- Unlicensed media is ingested.
- Missing sample requirements are ignored.
- VSS readiness is claimed without runtime proof.
- Prior certified outputs are mutated.

## Claim boundary

Allowed:
- “A VSS sample eligibility/ingest smoke was run.”
- “The sample ingest gate remains closed because required licensed sample evidence is missing.”
- “A structural ingest manifest exists for the validated local sample,” only if complete.

Forbidden:
- “VSS is ready.”
- “Licensed corpus acquired,” unless actual license/provenance evidence exists.
- “Traffic image/video analytics is operational.”
- “Camera inference/DeepStream/VSS runtime works,” unless separately proven by accepted runtime outputs.
