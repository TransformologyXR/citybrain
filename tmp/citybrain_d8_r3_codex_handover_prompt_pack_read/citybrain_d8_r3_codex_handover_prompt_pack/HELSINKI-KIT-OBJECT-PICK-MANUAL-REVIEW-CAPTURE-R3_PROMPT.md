# TASK PROMPT — HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3

## Goal

Convert the Helsinki R2 manual object-pick alignment packets into a bounded manual-review capture package suitable for demo evidence and later Kit/Composer review.

This task should not claim full object-level USD alignment. It should capture manual review status, preserve evidence, classify reviewed picks, and prepare a clean handoff for the final D8 demo/certified package.

## Upstream context

Use the most recent successful Helsinki R2 output, expected around:

- `outputs/helsinki_kit_object_pick_manual_alignment_r2/`
- `outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/`
- `outputs/d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/`

Known upstream facts:
- R1 consumed 2,980/2,980 CityGML building identity rows.
- R1 produced 2,980 CER candidate rows and 2,980 USD/CER sidecar candidate rows.
- R2 produced 20 manual object-pick alignment packets plus a lightweight USDA sidecar layer.
- Visual mesh remains `VISUAL_BACKDROP_ONLY` unless review evidence proves otherwise.

Discover actual roots from decision JSONs if path names differ.

## Required behavior

1. Load the R2 object-pick packets.
2. Validate each packet references:
   - CityBrain candidate/canonical entity ID
   - source CityGML ID or equivalent source object ref
   - USD/USDA prim path or suggested prim path
   - evidence refs
   - limitation refs
   - review state
3. Create a manual-review capture table for the 20 packets.
4. Classify each packet into one of:
   - `reviewed_aligned`
   - `reviewed_probable`
   - `reviewed_uncertain`
   - `reviewed_rejected`
   - `pending_review`
5. Only mark `reviewed_aligned` if there is explicit local review evidence, not merely a packet existing.
6. Preserve a conservative default of `pending_review` where evidence is insufficient.
7. Produce a Kit/Composer handoff note that tells an operator how to inspect picks manually.
8. Produce a demo-safe summary that can be consumed by the D8 final demo/handoff.

## Required outputs

Output root:

`outputs/helsinki_kit_object_pick_manual_review_capture_r3/`

Files:

- `HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json`
- `MANUAL_OBJECT_PICK_REVIEW_CAPTURE.csv`
- `MANUAL_OBJECT_PICK_REVIEW_CAPTURE.jsonl`
- `KIT_COMPOSER_MANUAL_REVIEW_HANDOFF.md`
- `HELSINKI_OBJECT_PICK_DEMO_SUMMARY.md`
- `HELSINKI_OBJECT_PICK_LIMITATIONS.md`
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
  "task": "HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3",
  "status": "PASS_WITH_LIMITATIONS",
  "upstream_roots": [],
  "packets_loaded": 0,
  "review_counts": {
    "reviewed_aligned": 0,
    "reviewed_probable": 0,
    "reviewed_uncertain": 0,
    "reviewed_rejected": 0,
    "pending_review": 0
  },
  "visual_mesh_status": "VISUAL_BACKDROP_ONLY",
  "object_level_alignment_claim": false,
  "demo_safe": true,
  "audits": {},
  "limitations": [],
  "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1"
}
```

## Acceptance criteria

Pass with limitations if:
- R2 packets are loaded and validated.
- 20 packets are captured, or all available R2 packets are captured with a clear count if fewer/more exist.
- Review classifications are conservative and evidence-backed.
- No full object-level alignment claim is made unless explicit manual review evidence exists.
- Kit/Composer review handoff exists.
- All audits pass.

Fail if:
- Upstream R2 packets cannot be located.
- Packet parsing fails.
- Outputs overclaim visual mesh/object alignment.
- Prior certified outputs are mutated.

## Claim boundary

Allowed:
- “20 manual object-pick packets were captured for review.”
- “A bounded Kit/Composer manual-review handoff exists.”
- “Some picks may be classified as aligned/probable/uncertain only according to captured review evidence.”

Forbidden:
- “Kalasatama USD object alignment is certified.”
- “The visual mesh has object-level identity.”
- “This is a production digital twin.”
