# IMPLEMENTATION NOTES — R8

Recommended implementation approach:

1. Load R7 package and parse:
   - `R7_CLOSEOUT_DECISION.json`
   - `R2_INPUT_LINEAGE_SUMMARY_R7.json`
   - `RUNTIME_HOST_ALLOCATION_R7.json`
   - `VSS_NARRATION_SIDECAR_R7.jsonl`
   - all R7 audits

2. Optionally load R2 package to cross-check:
   - candidate event hash
   - evidence bundle reference
   - candidate observations count

3. Build joined object:
   - keep R2 structured event as immutable base
   - attach VSS narration as `narration_sidecars[]`
   - do not merge VSS text into event fields

4. Produce source-depth CHECK:
   - R2 has structured object metadata: PASS
   - VSS has narration: PASS
   - frame image still absent unless separately exported: limitation
   - sample-media only: limitation
   - wall-clock timestamp absent: limitation

5. Produce final closeout decision and freeze ZIP.
