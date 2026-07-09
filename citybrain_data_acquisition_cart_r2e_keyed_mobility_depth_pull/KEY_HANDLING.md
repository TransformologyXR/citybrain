# Key Handling Policy — R2E

This package intentionally contains **no** LTA or TfL keys.

Use environment variables:

```powershell
$env:LTA_DATAMALL_ACCOUNT_KEY="<provided LTA DataMall REST key>"
$env:LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY="<provided Extended OBU SDK key>"
$env:TFL_PRIMARY_KEY="<provided TfL primary key>"
$env:TFL_SECONDARY_KEY="<provided TfL secondary key>"
```

Or use an untracked local env file copied from `secrets/lta_tfl.env.template`.

Rules:

- Do not commit `.env` files.
- Do not package credentials.
- Do not print keys.
- Do not persist full request URLs containing `app_key` values.
- Persist only redacted URL templates.
- Store failed response status/error class only; do **not** store failed response bodies.
- Store successful `200/201` provider payloads only under the external raw root.
- Treat the Extended OBU SDK key as key-present only; do not use it for ordinary DataMall REST calls.
- If any raw provider response echoes a key, delete it, patch the harvester, rerun, and rotate if necessary.
