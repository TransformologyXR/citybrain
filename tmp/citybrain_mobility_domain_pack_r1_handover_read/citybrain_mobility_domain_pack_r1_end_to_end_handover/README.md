# Mobility Domain Pack R1 End-to-End Handover

Created: 2026-06-30T13:38:40+00:00

This package replaces a standalone mobility preflight with an end-to-end Mobility Domain Pack R1 task.

The preflight is not removed; it is folded into Phase 0 of the R1 run. If enough inputs exist, Codex should continue through the full R1 build. If inputs are thin, it should still produce a bounded DATA_FIRST/context-only mobility pack rather than stopping too early.

Primary Codex prompt:

`RUN_THIS_IN_CODEX.md`
