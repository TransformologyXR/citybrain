# ACCEPTANCE CHECKS

## Must pass for PASS status

- Runtime configured: true
- Probe attempted: true
- Probe executed: true
- Probe status: reachable/success
- Timeout bounded
- Runtime config redacted
- JSON parse: PASS
- HASH_MANIFEST: PASS
- Source-class separation: PASS
- Claim-boundary audit: PASS
- No-action audit: PASS
- Secret audit: PASS
- Candidate event mutation audit: PASS

## Must remain partial if

- Runtime configured: false
- Probe attempted: false
- Probe executed: false
- Endpoint unreachable
- Command exits non-zero
- Probe times out
- Protocol unsupported

## Must fail if

- Any secret/token is written to artifacts
- VSS output is treated as sensor fact
- VSS output modifies candidate observations/events
- Package claims legal/certified finding
- Package creates official case/ticket/action
- Package fabricates narration or connectivity evidence
