# CityBrain Metropolis/VSS — BMD-45 Human Review Benchmark Packet R20

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-HUMAN-REVIEW-BENCHMARK-PACKET-R20`

This handoff converts the verified R19 replay benchmark/regression outputs into an operator/cockpit-ready human-review benchmark packet.

R20 is **not** a new detector, not a live-CCTV task, and not an accuracy/certification claim. It packages review evidence from R19 so an operator can inspect:

- selected BMD-45 frames as external media references;
- dataset annotations as `dataset_annotation`;
- DeepStream/Metropolis outputs as `sensor_inferred`;
- IoU match summaries and confidence bands;
- false-positive and missed-annotation review lists;
- drift/benchmark scorecard;
- limitation and boundary labels.

Expected output root:

`outputs/main_citybrain_metropolis_vss_bmd45_human_review_benchmark_packet_r20`

Expected freeze ZIP:

`METROPOLIS_VSS_BMD45_HUMAN_REVIEW_BENCHMARK_PACKET_R20_PACKAGE.zip`
