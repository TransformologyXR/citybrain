# IMPLEMENTATION NOTES — R5

## Recommended runner structure

1. `validate_r4_package(input_r4_zip)`
2. `build_vss_input_packet(r4_context)`
3. `resolve_runtime_config(args, env)`
4. `execute_vss_runtime(config, input_packet)`
5. `normalize_vss_output(raw_capture)`
6. `run_guardrails(sidecars, r4_context)`
7. `write_decision_and_closeout()`
8. `write_json_parse_report()`
9. `write_hash_manifest()`
10. `freeze_zip()`

## Command execution guidance

- Use a timeout.
- Prefer `subprocess.run(..., timeout=timeout_sec, capture_output=True, text=True)`.
- Replace `{input_json}` and `{output_json}` tokens before execution.
- Do not package full command if it may contain tokens or endpoints; store redacted mode/source only.
- If a command is configured but lacks `{input_json}` and `{output_json}`, still run only if it is a known safe wrapper; otherwise partial-failed-config is safer.

## Endpoint execution guidance

- POST the VSS input packet as JSON.
- Record status code and whether response body was captured.
- Redact endpoint URL.
- Do not package auth headers.

## Normalization guidance

Accept any of these raw forms:

- JSON object with `text`, `narration`, `caption`, `summary`, or `response`
- JSON list of narration objects
- plain text stdout/response

Emit at most one sidecar unless `--max-narration-records` says otherwise.

## Guardrail guidance

Scan normalized prose for forbidden terms and unsupported claim patterns.
Do not overfit to exact wording: the check should catch legal/identity/action/live
monitoring claims even if phrased differently.
