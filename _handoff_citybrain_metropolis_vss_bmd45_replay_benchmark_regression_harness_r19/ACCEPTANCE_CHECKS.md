# ACCEPTANCE CHECKS — R19

## PASS requires

- R18 input validation PASS.
- R18 baseline metrics loaded.
- Benchmark config emitted.
- Baseline scorecard emitted.
- Regression assertions emitted with documented tolerance bands.
- Rerun execution report emitted; either executed successfully or explicitly marked not run with a bounded reason.
- Final audits PASS.
- JSON/JSONL parse PASS.
- Hash manifest PASS.
- No packaged media files unless explicitly declared.

## Acceptable partial

Use `PARTIAL_METROPOLIS_VSS_BMD45_REPLAY_BENCHMARK_CONTRACT_READY_RERUN_PENDING` when benchmark contract and scorecard exist but DeepStream rerun cannot execute.

## FAIL conditions

- Dataset annotations treated as official truth.
- DeepStream detections treated as findings.
- VSS treated as fact source.
- Live CCTV claimed without a real RTSP/live source.
- Ticket, dispatch, identity, legal/certified claim, or action created.
- Secrets packaged or logged.
