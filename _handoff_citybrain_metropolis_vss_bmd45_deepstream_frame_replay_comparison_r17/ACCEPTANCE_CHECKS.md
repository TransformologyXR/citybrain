# ACCEPTANCE CHECKS — R17

## Required checks

- ZIP integrity PASS
- JSON parse PASS
- JSONL parse PASS
- Hash manifest verifies all packaged files
- R16 package validation PASS
- R16 selected source is BMD-45
- R16 candidate fixture records loaded
- BMD-45 external media refs loaded
- Frame fetch/cache SHA verification completed or explicitly partial
- DeepStream input prep completed
- DeepStream execution attempted and status recorded
- No fabricated detections
- Source-class separation PASS
- Dataset annotation boundary PASS
- Claim boundary PASS
- No-action PASS
- Secret audit PASS
- VSS-not-fact-source PASS

## PASS minimum

A PASS requires actual DeepStream execution, exported metadata, and comparison computation.

## Partial minimum

A partial is acceptable if the frame replay source is prepared but DeepStream execution is blocked, provided no detections are fabricated and all boundaries pass.
