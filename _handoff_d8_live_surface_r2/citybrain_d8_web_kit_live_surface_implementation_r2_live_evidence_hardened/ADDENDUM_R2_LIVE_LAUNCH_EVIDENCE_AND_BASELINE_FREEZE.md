# ADDENDUM R2 — Live Launch Evidence, Moment Parity, and Baseline Freeze Hardening

Generated: 2026-07-01
Applies to: `citybrain_d8_web_kit_live_surface_implementation` prompt pack
Status: **mandatory patch — apply before running the Web + Kit live surface sprint.**

## 1. Why this patch exists

This sprint must not produce another green report over source files that nobody actually launched. Web and Kit surfaces are not proven alive by schema validation alone.

R2 therefore hardens four gates:

1. **Web live launch evidence is mandatory.** A local server must start, the page must load the known Mobility Access runtime bundle, and a known value from that bundle must appear in the rendered DOM or screenshot evidence.
2. **Kit launch status must be honest.** If Omniverse Kit is available, the extension must be enabled in a real Kit runtime and log proof must be captured. If Kit is not runnable, record `KIT_RUNTIME_UNAVAILABLE` as a first-class limitation; do not imply Kit was live.
3. **Moment parity is mandatory before capture readiness.** Every D8 demonstrable moment must have a render home on the maintained surface before the surface is frozen for capture/viewer validation.
4. **`one_truth_index.json` is authoritative.** Drift means divergence from the canonical runtime bundle, not merely Web and Kit agreeing with each other.

## 2. Maintained source posture

This sprint creates maintained product source, not immutable output artifacts:

```text
outputs/ = evidence ledger
apps/ + packages/ = maintained product source
packages/fixtures/mobility_access/ = read-only certified-state projection
```

The milestone freeze snapshots a **baseline** for capture and external viewer validation. It does not make `apps/` or `packages/` permanently immutable. Later remediation may edit the maintained source, but must identify which frozen baseline it changes.

## 3. Web technology choice

Default to structured vanilla HTML/CSS/JS for this sprint. Do not introduce React/Vite/Next or internet package installs. The goal is an auditable local demonstrator with minimal toolchain risk. A framework can be revisited after the surface is demonstrably alive.

## 4. Hard-gate artifacts added by R2

Required new/strengthened artifacts:

```text
WEB_LOCAL_LAUNCH_EVIDENCE.json
WEB_RENDERED_DOM_ASSERTION_REPORT.json
WEB_LAUNCH_SCREENSHOT_OR_DOM_CAPTURE.*
KIT_RUNTIME_PROBE_REPORT.json
KIT_EXTENSION_LOAD_SMOKE_REPORT.json or KIT_RUNTIME_UNAVAILABLE_REPORT.json
LIVE_SURFACE_MOMENT_PARITY_REPORT.json
ONE_TRUTH_AUTHORITY_REPORT.json
SURFACE_BASELINE_FREEZE_SEMANTICS.md
```

A green closeout must not rely on run instructions alone for the Web surface. Instructions may supplement evidence; they cannot substitute for evidence.
