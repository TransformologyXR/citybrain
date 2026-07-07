# CityBrain Agent Instructions

## Progress Log

Every CityBrain task must append a concise entry to `progress.md` before final response.

Use this shape:

```text
## YYYY-MM-DD HH:MM TZ - Short Task Name

- Status: done / partial / blocked
- Summary: one or two sentences describing what changed or what was learned.
- Files/artifacts: key files, commits, outputs, or publications touched.
- Verification: tests, audits, commands, or "not run" with reason.
- Boundaries: note anything intentionally excluded, deferred, or not claimed.
```

Keep entries factual and compact. Do not put secrets, passwords, API keys, raw data, or bulky generated output in `progress.md`. If a task is read-only, still log the finding and verification.
