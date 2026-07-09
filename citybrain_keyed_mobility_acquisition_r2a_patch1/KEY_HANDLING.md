# Key Handling Policy

This package intentionally does **not** contain the LTA or TfL keys.

Use one of these approaches:

## PowerShell environment variables

```powershell
$env:LTA_DATAMALL_ACCOUNT_KEY="<provided LTA DataMall API Account Key>"
$env:LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY="<provided Extended OBU SDK Account Key>"
$env:TFL_PRIMARY_KEY="<provided TfL primary key>"
$env:TFL_SECONDARY_KEY="<provided TfL secondary key>"
```

## Untracked local env file

Copy `secrets/lta_tfl.env.template` to a local path outside git, fill it in, and run with:

```powershell
python scripts\harvest_lta_tfl_keyed_sources.py --env-file C:\data\citybrain\secrets\lta_tfl.env --smoke ...
```

## Rules

- Do not commit `.env` files.
- Do not package raw credentials in ZIPs.
- Do not print keys in logs.
- Do not persist request URLs containing `app_key` values.
- For TfL, write sanitized URL templates only.
- For LTA, write endpoint paths and auth status only.
- Treat the Extended OBU SDK key as SDK-specific; do not use it for ordinary LTA DataMall REST APIs unless a specific SDK task requires it.
- If keys are accidentally committed or shared outside the private environment, rotate them.
