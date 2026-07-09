# TASK: MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-ACQUISITION-R2

## Purpose
Acquire or prepare the smallest legally usable, privacy-aware, metadata-complete CCTV/video sample corpus required to move the VSS lane from acquisition-readiness documentation toward a real bounded sample gate. This task is an acquisition/sample governance task, not VSS runtime implementation.

## Context
Prior D8 results established that the VSS readiness package exists but VSS gates remain correctly closed because no audited licensed corpus, complete camera metadata, oracle labels, or runtime VSS stack have been proven. Singapore public traffic image routes remain blocked or gated: data.gov.sg returned 403 and LTA DataMall requires a valid AccountKey.

## Inputs
Use existing outputs if present:
- outputs/citybrain_d8_parallel_prompt_pack_closeout/
- outputs/main_citybrain_d8_vss_licensed_corpus_acquisition_r1/ or equivalent R1 VSS readiness output
- outputs/data_gap_ledger_and_priority_matrix/
- camera/video media inventory from D8 readiness scouts
- secret/no-action/claim-boundary audit conventions from prior D8 tasks

Do not assume any external source is usable unless access, license, privacy posture, and intended use are documented.

## Hard boundaries
- Do not download large video datasets.
- Do not scrape or bypass CAPTCHA, form blocks, authentication, robots, or access controls.
- Do not use public CCTV or traffic imagery unless license/access terms permit the intended local demo/research use.
- Do not claim NVIDIA VSS readiness.
- Do not claim production video analytics, surveillance, enforcement, legal, or autonomous action capability.
- Do not include secrets, SDK keys, tokens, private URLs, or credentials in outputs.
- Do not mutate certified prior outputs.

## Required work

### 1. Source candidate ledger
Create a candidate ledger for at least these source families:
- user-owned or TXR-owned sample footage
- synthetic or simulator-generated CCTV-like clips
- public-domain or permissively licensed traffic / city video datasets
- licensed commercial/demo samples, if available
- prior local media refs from D8 inventory
- LTA/DataMall and Singapore data.gov traffic image routes, preserving blocked/gated status

For each candidate, record:
- source_name
- source_type
- access_status
- license_status
- privacy_status
- metadata_completeness
- camera_metadata_available
- oracle_label_feasibility
- expected_sample_count
- download_size_class
- permitted_use_summary
- blocker_reason
- recommended_disposition

### 2. Minimal sample acceptance contract
Define a strict R2 sample acceptance contract.

Minimum fields per accepted clip/image sequence:
- corpus_item_id
- source_ref
- license_ref or license_note
- allowed_use
- privacy_review_state
- camera_id
- camera_location_type
- camera_pose_available
- timestamp_available
- frame_rate_or_capture_interval
- resolution
- scene_type
- event_or_no_event_label
- oracle_label_ref
- evidence_clip_ref or local_path
- limitations

### 3. Oracle-label plan
Create a small oracle plan for candidate event types only:
- person present
- vehicle present
- restricted-zone entry, if zone metadata exists
- PPE/no-PPE only if footage is construction/PPE-relevant and annotation is legally usable
- camera health/offline/blocked only if sample supports it
- no-event negative examples

Oracle labels must be human-readable and deterministic. If no legal/usable sample is found, produce an empty oracle template and keep the gate closed.

### 4. Privacy and legal posture summary
For every candidate source, classify:
- approved_for_local_sample
- needs_owner_permission
- needs_license_purchase
- blocked_by_auth
- blocked_by_terms
- blocked_by_privacy
- unsuitable_for_vss_sample

### 5. Gate decision
Emit a machine-readable VSS R2 gate decision:
- `VSS_SAMPLE_CORPUS_GATE = OPEN_SAMPLE_READY` only if at least one sample item has usable license/access, sufficient metadata, and oracle labeling path.
- `VSS_SAMPLE_CORPUS_GATE = CLOSED` otherwise.

Do not open runtime/VSS gates in this task.

## Required outputs
Create output root:
`outputs/main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/`

Required files:
- `VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_DECISION.json`
- `VSS_SOURCE_CANDIDATE_LEDGER.csv`
- `VSS_SOURCE_CANDIDATE_LEDGER.json`
- `VSS_MINIMAL_SAMPLE_ACCEPTANCE_CONTRACT.json`
- `VSS_ORACLE_LABEL_PLAN.json`
- `VSS_PRIVACY_LEGAL_POSTURE_SUMMARY.md`
- `VSS_SAMPLE_GATE_DECISION.json`
- `VSS_R2_LIMITATIONS.md`
- `HASH_MANIFEST.sha256`
- `RUN_AUDIT.json`

## Audits
Must run and record:
- JSON parse audit
- no prior output mutation audit
- secret scan
- license/access claim audit
- privacy-boundary audit
- no production/VSS/legal/certified/live/autonomous claim audit
- hash manifest verification

## Acceptance criteria
Pass with limitations if:
- candidate sources are classified honestly
- source blockers are preserved rather than bypassed
- sample acceptance contract exists
- oracle label plan exists
- VSS gates remain closed unless a genuinely licensed, metadata-sufficient sample is proven
- all audits pass

Expected final status:
`PASS_MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_WITH_LIMITATIONS`

If no usable sample can be legally accepted, still pass with limitations if the closed-gate evidence is complete and honest.
