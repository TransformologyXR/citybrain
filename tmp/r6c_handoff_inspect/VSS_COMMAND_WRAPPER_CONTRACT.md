# VSS COMMAND WRAPPER CONTRACT — R6C

A usable command should be a bounded health/readiness probe.

Expected behavior:

```text
exit code 0 = healthy/reachable
non-zero exit = not healthy/reachable
stdout/stderr = redacted and excerpted only
timeout = partial/fail depending on risk
```

The command must not perform official actions or modify candidate events.
