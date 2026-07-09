You are implementing `MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-COCKPIT-SURFACE-RUNTIME-SMOKE-R22`.

Use the R21 package as the source of truth. Do not re-run DeepStream, Metropolis,
VSS, or BMD-45 fetch unless explicitly needed for a non-mutating external-media
link check.

Create:

`scripts/run_main_citybrain_metropolis_vss_bmd45_cockpit_surface_runtime_smoke_r22.py`

Output root:

`outputs/main_citybrain_metropolis_vss_bmd45_cockpit_surface_runtime_smoke_r22`

Expected freeze ZIP:

`METROPOLIS_VSS_BMD45_COCKPIT_SURFACE_RUNTIME_SMOKE_R22_PACKAGE.zip`

Required behavior:

1. Validate R21 input package and hash manifest.
2. Load cockpit tile, app fixture, frame review cards, and human-review consumption fixture.
3. Exercise one of these, in order:
   - existing cockpit/app route if available;
   - local static HTML/JSON review surface if app route is not available;
   - contract-only render fixture if neither runtime is available.
4. Emit a cockpit surface runtime report.
5. Verify that source-class labels remain:
   - BMD-45 labels = `dataset_annotation`
   - DeepStream/Metropolis = `sensor_inferred`
   - VSS = `model_generated_narrative_not_fact_source`
6. Verify all review cards show or carry candidate-review-only boundary labels.
7. Preserve external media refs without packaging media files.
8. Emit final audits and closeout decision.

Do not claim live CCTV, production UI readiness, official findings, tickets,
dispatch, identity/biometric inference, legal/certified conclusions, or action.
