# PACKAGE CONTRACT — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

## Output root

```text
outputs/main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6
```

## Freeze ZIP

```text
METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip
```

## Required artifact contract

| File | Purpose |
|---|---|
| `R5_PACKAGE_VALIDATION_R6.json` | Validates uploaded/input R5 package and preserves R2/R5 truth |
| `VSS_RUNTIME_CONFIGURATION_R6.json` | Redacted runtime config source and selected mode |
| `VSS_RUNTIME_CONNECTIVITY_PROBE_R6.json` | Probe attempted/executed/result/latency/status |
| `VSS_RUNTIME_READINESS_DECISION_R6.json` | Whether runtime is ready for a future narration smoke |
| `SOURCE_CLASS_SEPARATION_AUDIT_R6.json` | Proves sensor-inferred vs model-generated separation |
| `CLAIM_BOUNDARY_AUDIT_R6.json` | Proves no confirmed violation/finding/action claims |
| `NO_ACTION_AUDIT_R6.json` | Proves no official/ticket/dispatch/control/enforcement action |
| `SECRET_AUDIT_R6.json` | Proves no tokens/passwords/API keys leaked |
| `VSS_CONFIGURATION_GUARDRAIL_REPORT_R6.json` | Checks configuration safety and no fabrication |
| `CHECK_RUNTIME_CONNECTIVITY_REPORT_R6.json` | CHECK dimension report for runtime readiness |
| `JSON_PARSE_REPORT_R6.json` | JSON/JSONL validation |
| `HASH_MANIFEST.json` | SHA-256 manifest over package files |
| `METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_DECISION.json` | Machine decision |
| `METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json` | Final closeout decision |

## Required manifest rules

- Manifest must cover every file in the freeze ZIP except the ZIP itself.
- Manifest must use SHA-256.
- Hash verification must pass before closeout.

## Package must not contain

- unredacted bearer tokens
- API keys
- passwords
- private keys
- full remote credentials
- fabricated VSS narration
- official records or ticket/action payloads
