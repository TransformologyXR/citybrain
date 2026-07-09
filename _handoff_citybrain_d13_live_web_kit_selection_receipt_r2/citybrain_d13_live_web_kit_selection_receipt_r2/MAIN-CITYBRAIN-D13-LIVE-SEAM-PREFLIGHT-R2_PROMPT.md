# MAIN-CITYBRAIN-D13-LIVE-SEAM-PREFLIGHT-R2

Verify inputs and stop early if the live seam cannot be attempted truthfully.

Required checks:
1. Locate previous D13 seam outputs:
   - `D13_SEAM_MILESTONE_FREEZE_DECISION.json`
   - `WEB_KIT_SELECTION_BRIDGE_CONTRACT.json`
   - `ONE_TRUTH_SEAM_COMPARISON_REPORT.json`
2. Locate and hash overlay files:
   - `packages/fixtures/d11_operator_workflow_review_workspace/runtime_overlay/D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json`
   - `packages/fixtures/d13_spatial_twin_omniverse_one_truth/runtime_overlay/D13_SPATIAL_ONE_TRUTH_BINDINGS.json`
3. Verify Kit app/extension launch command or documented path exists.
4. Verify web app local server command or existing dev server path exists.
5. Verify no D14 router work is attempted and no D11 fake sessions are created.

Output:
`D13_LIVE_SEAM_PREFLIGHT_DECISION.json`

Statuses:
- `PASS_D13_LIVE_SEAM_PREFLIGHT`
- `PARTIAL_D13_LIVE_SEAM_PREFLIGHT_ENV_BLOCKED`
- `FAIL_D13_LIVE_SEAM_PREFLIGHT_BOUNDARY_OR_INPUT_ERROR`
