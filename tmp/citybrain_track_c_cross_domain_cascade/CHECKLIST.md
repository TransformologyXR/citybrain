# Checklist

## Before starting

- Confirm Track S, B, R, and I are green.
- Confirm current sprint closeout/handover is green if running beyond preflight.
- Confirm no commit/staging unless user explicitly requests.
- Preserve existing unrelated worktree changes.

## Required outputs per task

Every task must produce:
- decision JSON
- input artifact index
- validation report
- claim boundary audit
- no-action boundary audit
- no-mutation audit
- secret audit
- hash manifest
- local open index

## Track-level acceptance

Pass only if:
- cascade paths are evidence-backed or explicitly fixture/replay context
- unresolved/quarantined contexts are preserved
- no new canonical truth is invented
- no action/execution/dispatch/control claim is introduced
- reviewed option-set attachment is schema-compatible
- quality gate discriminates good vs broken cascade outputs
