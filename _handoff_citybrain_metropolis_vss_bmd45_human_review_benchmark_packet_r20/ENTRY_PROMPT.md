# ENTRY PROMPT — R20 Human Review Benchmark Packet

You are implementing `MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-HUMAN-REVIEW-BENCHMARK-PACKET-R20`.

Create:

`scripts/run_main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20.py`

Output root:

`outputs/main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20`

Consume the verified R19 package:

`outputs/main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19/METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_PACKAGE.zip`

## Implementation

1. Validate the R19 package:
   - ZIP integrity.
   - JSON/JSONL parse.
   - hash manifest.
   - closeout status equals `PASS_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_REGRESSION_HARNESS_R19_WITH_LIMITATIONS`.

2. Extract the R19 benchmark materials:
   - candidate observations JSONL;
   - frame comparison records JSONL;
   - baseline scorecard;
   - threshold calibration delta;
   - external media refs;
   - drift review packet;
   - source-class and no-action audits.

3. Build a human-review benchmark packet:
   - overall summary;
   - per-frame cards;
   - external media references only, no packaged image/video files;
   - dataset annotation summary;
   - sensor-inferred candidate summary;
   - IoU comparison summary;
   - confidence band summary;
   - false-positive review list;
   - missed-annotation review list;
   - limitation labels;
   - human review required.

4. Build cockpit tile fixtures:
   - one overall benchmark tile;
   - per-frame review card fixtures;
   - status labels;
   - source-class labels;
   - action boundary labels;
   - external media refs.

5. Run audits:
   - source-class separation;
   - claim boundary;
   - no-action;
   - VSS-not-fact-source;
   - secret audit;
   - packaged-media audit.

6. Freeze a ZIP:
   `METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_PACKAGE.zip`

## Do not

- Do not reclassify BMD-45 annotations as official truth.
- Do not reclassify DeepStream output as a finding.
- Do not claim live CCTV.
- Do not create tickets, dispatches, identities, legal conclusions, or actions.
- Do not package media unless explicitly requested; use external media refs.
