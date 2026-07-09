# IMPLEMENTATION NOTES — R6C

## Redaction

Before writing any artifact, redact:

- API keys
- bearer tokens
- query strings containing token/key/auth
- passwords
- long local secrets
- signed URLs

Recommended redaction patterns:

```text
token=...
api_key=...
key=...
Authorization: Bearer ...
password=...
sig=...
X-API-Key: ...
```

## Endpoint mode

Use a simple HTTP GET against:

```text
{CITYBRAIN_VSS_ENDPOINT}{CITYBRAIN_VSS_HEALTH_PATH}
```

Default health path:

```text
/health
```

Record only:

- redacted endpoint
- HTTP status
- content type
- latency
- redacted response excerpt
- success/failure classification

## Command mode

Run a bounded command with timeout.

Recommended: require a command that is itself a health probe, not a full inference run.

Capture only redacted excerpts.

## Do not run narration

R6C is readiness only. R7 owns narration.
