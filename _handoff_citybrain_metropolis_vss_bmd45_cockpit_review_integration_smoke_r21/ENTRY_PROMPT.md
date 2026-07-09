# ENTRY PROMPT — R21 Cockpit Review Integration Smoke

You are implementing:

`MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-REVIEW-INTEGRATION-SMOKE-R21`

## Context

R20 closed as `PASS_METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_WITH_LIMITATIONS`.
It produced a human-review benchmark packet and cockpit tile fixture from R19 benchmark outputs.

## Task

Create:

`scripts/run_main_citybrain_metropolis_vss_bmd45_cockpit_review_integration_smoke_r21.py`

Output root:

`outputs/main_citybrain_metropolis_vss_bmd45_cockpit_review_integration_smoke_r21`

Freeze ZIP:

`METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_PACKAGE.zip`

## Implementation requirements

1. Locate and validate the R20 package.
2. Parse R20 closeout, human-review packet, cockpit tile fixture, frame review cards, review lists, and audits.
3. Emit a cockpit integration packet suitable for local app/cockpit consumption.
4. Emit review tile fixtures and per-frame card fixtures.
5. Emit an action policy showing allowed review-only actions and forbidden official/operational actions.
6. Preserve source-class labels.
7. Preserve external-media references without packaging media.
8. Run schema and boundary audits.
9. Create a closeout decision and hash manifest.
10. Do not rerun DeepStream, VSS, or fetch BMD-45 frames.

## PASS criteria

PASS only if:
- R20 input validation passes.
- cockpit integration packet is emitted.
- cockpit tile fixture is emitted.
- frame review cards are emitted.
- external media refs are preserved.
- review-only action policy is present.
- all source/boundary/no-action/secret/VSS-not-fact-source audits pass.

## PARTIAL criteria

Use partial if:
- the app/cockpit surface is not available and only fixture validation is performed,
- but the fixture contract is complete and safe.

## FAIL criteria

Fail if:
- source classes are collapsed,
- VSS is treated as a fact source,
- DeepStream detections are treated as findings,
- BMD-45 labels are treated as official truth,
- any ticket, dispatch, identity, legal claim, official record, or action is created.

