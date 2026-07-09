# HTTP Client Policy — R2E

R2A proved that bare `urllib` defaults can be blocked by provider edges even when browser access and keys are valid. All CityBrain HTTP harvesters must use an explicit client profile.

Required headers:

```text
User-Agent: CityBrain-R2E/1.0
Accept: application/json
```

Provider-specific auth:

```text
LTA DataMall REST:
  Header: AccountKey: <env:LTA_DATAMALL_ACCOUNT_KEY>
  Header: accept: application/json

TfL Unified API:
  Query parameter: app_key=<env:TFL_PRIMARY_KEY or env:TFL_SECONDARY_KEY>
  Log only: app_key=REDACTED
```

Failure-body policy:

- Successful `200/201` payloads may be persisted under the external raw root.
- Failed provider response bodies must not be persisted, because they may echo request metadata or key values.
- Ledgers should preserve status code, provider, endpoint template, redacted URL, retry/key slot, and error class only.

Rate policy:

- Use bounded sleeps between requests.
- Allow configurable `--sleep-sec`.
- Do not implement uncontrolled infinite crawls.
- For paginated endpoints, stop on empty page, repeated page hash, provider error, or `--max-lta-pages`.
