# ACCEPTANCE CHECKS — R16

PASS checks:
- Dataset source selected.
- License/provenance gate PASS or clearly PARTIAL.
- No restricted media packaged without rights.
- Offline replay sample manifest emitted.
- Camera/source registry updated.
- Candidate-observation fixture emitted from actual annotations/metadata, or explicitly marked synthetic fixture.
- Source-class separation PASS.
- Claim-boundary PASS.
- No-action PASS.
- Secret audit PASS.
- JSON/JSONL parse PASS.
- Hash manifest PASS.

Dataset decision gates:
- BMD-45: may pass as fixed-CCTV image/frame replay if attribution recorded.
- AI City CityFlowV2/WTS: license review required before use.
- VIRAT: usage-agreement review required before use.
- BDD100K: fallback only; label dashcam/traffic-like, not CCTV.
