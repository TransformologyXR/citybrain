# Data source endpoint confirmation — R2A Patch 1

Status: `CURRENT_ENDPOINTS_CONFIRMED_FOR_CODEX_RETRY_WITH_NETWORKED_RUNTIME`

## LTA DataMall

Use the REST base URL:

```text
https://datamall2.mytransport.sg/ltaodataservice
```

Authentication pattern:

```text
Header: AccountKey: <LTA_DATAMALL_ACCOUNT_KEY>
Header: accept: application/json
```

The assistant sandbox and web fetcher could not fetch the DataMall base page directly, but the official LTA API guide/search result confirms the `datamall2.mytransport.sg/ltaodataservice` endpoint family, including `BusStops`, `TrafficIncidents`, `RoadWorks`, and `Traffic-Imagesv2`. Treat this as a network/runtime issue, not an obsolete endpoint.

## TfL Unified API

Use the REST base URL:

```text
https://api.tfl.gov.uk
```

Swagger/OpenAPI document:

```text
https://api.tfl.gov.uk/swagger/docs/v1
```

Authentication pattern:

```text
Query parameter: app_key=<TFL_PRIMARY_KEY or TFL_SECONDARY_KEY>
```

Patch 1 changes the road status endpoint from `/Road/All/Status` to `/Road/all/Status`, matching the swagger path form `/Road/{ids}/Status` with `ids=all`.

## Secret handling

No keys are packaged. Codex should set them through environment variables or a local untracked env file.
