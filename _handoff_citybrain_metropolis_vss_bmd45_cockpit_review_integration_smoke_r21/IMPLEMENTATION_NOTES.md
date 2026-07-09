# IMPLEMENTATION NOTES — R21

- Prefer fixture generation over app mutation.
- If the web/cockpit app path exists, produce a load report only; do not require UI screenshots for PASS.
- Keep this bounded to local files and fixtures.
- Use external media refs from R20.
- Do not package media.
- Do not rerun DeepStream or VSS.
- Preserve R20 baseline metrics for traceability.
