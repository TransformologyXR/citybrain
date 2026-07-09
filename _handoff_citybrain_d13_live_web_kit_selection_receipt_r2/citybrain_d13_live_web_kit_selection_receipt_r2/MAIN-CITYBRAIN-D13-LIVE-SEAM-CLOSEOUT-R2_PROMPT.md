# MAIN-CITYBRAIN-D13-LIVE-SEAM-CLOSEOUT-R2

Close out the live seam task.

Output:
`D13_LIVE_SEAM_CLOSEOUT_DECISION.json`

Allowed statuses:
- `PASS_D13_LIVE_WEB_KIT_SELECTION_SEAM_WITH_LIMITATIONS`
- `PARTIAL_D13_LIVE_SEAM_ONE_WAY_ONLY`
- `PARTIAL_D13_LIVE_SEAM_LOG_ONLY`
- `PARTIAL_D13_LIVE_SEAM_ENV_BLOCKED`
- `FAIL_D13_LIVE_SEAM_BOUNDARY_OR_PARITY`

Record:
- live receipt status by direction
- one-truth parity
- negative command results
- process cleanup
- limitations
- exact next task if still partial
