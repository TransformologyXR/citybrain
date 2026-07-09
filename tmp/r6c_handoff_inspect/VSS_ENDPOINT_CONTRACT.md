# VSS ENDPOINT CONTRACT — R6C

A usable endpoint should expose a bounded health/readiness path.

Minimum expected health response:

```json
{
  "status": "ok"
}
```

Other response shapes may be accepted if the probe can clearly classify the runtime as reachable and healthy.

R6C must not send media or object metadata for endpoint health probing unless explicitly configured and bounded.
