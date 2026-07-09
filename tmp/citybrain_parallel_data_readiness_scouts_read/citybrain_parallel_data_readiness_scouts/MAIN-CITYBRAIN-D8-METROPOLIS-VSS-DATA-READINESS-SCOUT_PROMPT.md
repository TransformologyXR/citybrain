# MAIN-CITYBRAIN-D8-METROPOLIS-VSS-DATA-READINESS-SCOUT

Goal: determine what is needed before any Metropolis/VSS claim is made.

Do not deploy or claim Metropolis/VSS unless the real stack runs and produces audited outputs.

Inspect local environment and available assets:
- GPU/driver/docker readiness if safely checkable
- existing D7 candidate observation media
- licensed/public video clips or camera image snapshots available locally
- any VSS/DeepStream/Metropolis repo/docs/container pointers already present
- disk and model/runtime constraints

Outputs:
- METROPOLIS_VSS_READINESS_MATRIX.json
- VIDEO_CORPUS_REQUIREMENTS.md
- VSS_OUTPUT_CONTRACT_DRAFT.json
- VIDEO_TO_EVIDENCE_BUNDLE_MAPPING.md
- PRIVACY_AND_BOUNDARY_LEDGER.md
- STACK_STATUS_REPORT.json with DATA_READY / STACK_READY / SAMPLE_OUTPUT_READY / NOT_RUN
- VALIDATION_REPORT.json
- HASH_MANIFEST.json

Readiness dimensions:
- licensed video corpus present
- camera/source metadata present
- query set present
- expected-output oracle present
- runtime available
- model/container available
- output-to-EvidenceBundle mapper defined
- no identity/biometric/legal/surveillance claim

If no suitable video corpus exists, return DATA_NOT_READY with exact next data acquisition tasks.
