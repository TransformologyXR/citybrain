# Checklist — Track I Inverse Dynamics

## Before running
- Commit/backup Track B and Track R outputs if needed.
- Confirm Track S, Track B, Track R, and Track D are green.
- Confirm this lane is local/replay review-only.

## During running
- Preserve option/proposal boundary.
- Ensure do-nothing baseline is mandatory.
- Preserve no-safe-option / abstain state.
- Keep all execution states `not_executed`.
- Attach simulation refs and similar-case refs.
- Run golden quality checks before closeout.
- Block/log unsafe actions and unsafe promotions.

## After running
- Upload closeout/freeze ZIP for validation.
- Do not start heavy cascade/perception lanes until inverse dynamics is validated.
