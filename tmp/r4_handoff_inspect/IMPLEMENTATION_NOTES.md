# IMPLEMENTATION NOTES — R4

## Why R4 exists

R3 was clean but partial because VSS was not configured. That is the correct result. R4 should add a real runtime adapter instead of pretending the model executed.

## Recommended implementation shape

Keep the runner mostly deterministic:

1. validate R3 package;
2. extract R2/R3 truth;
3. build R4 VSS input packet;
4. detect runtime mode:
   - command
   - endpoint
   - not configured
5. execute if configured;
6. capture raw output;
7. normalize to sidecar records;
8. run guardrails;
9. emit decision and closeout;
10. freeze package.

## Runtime output tolerance

The adapter should tolerate:

- JSON object with `narration_text`
- JSON object with `text`
- JSONL records
- plain text stdout, normalized into one sidecar if safe

But do not accept output that violates claim boundaries.

## Secret handling

Redact command/endpoint values in reports. It is acceptable to record runtime mode, return code, timeout, and whether execution occurred.
