# Known Blockers / Caveats — R2E

## Product boundary

LTA and TfL are Singapore/London mobility donor/context feeds. They are not Dubai facts and do not create official Dubai mobility truth.

## Raw data volume

R2E may generate much more raw data than R2A. Raw payloads must remain under the external raw root and must not be committed or packaged.

## LTA caveats

- Standard REST uses the DataMall REST AccountKey, not the Extended OBU SDK key.
- Paginated endpoints use `$skip` in pages of 500 where supported.
- Dynamic snapshot endpoints can change at provider cadence; R2E captures snapshots, not historical truth unless repeated snapshots are scheduled.
- Traffic camera metadata may change; store metadata and URLs/references, not large image media, unless a separate media-acquisition task is opened.

## TfL caveats

- TfL Unified API uses `app_key` query authentication.
- A normal User-Agent header is required by our harvester policy after R2A exposed edge blocking of bare urllib.
- Some TfL feeds are downloadable static files outside the Unified API; R2E focuses on keyed REST depth only.
- Streaming/password/IP-locked APIs are out of R2E scope.

## Extended OBU SDK

The SDK key is present in the user environment, but R2E does not call SDK libraries or SDK-specific endpoints. Open a dedicated `OBU-SDK-SCOUT` task if needed.
