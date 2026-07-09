# Data Sources Confirmation — R2E

## LTA DataMall

Base REST URL:

```text
https://datamall2.mytransport.sg/ltaodataservice
```

Authentication:

```text
Header: AccountKey: <LTA_DATAMALL_ACCOUNT_KEY>
Header: accept: application/json
```

DataMall publishes static and dynamic / real-time land-transport datasets. Dynamic APIs are available to registered subscribers with an Account Key.

## TfL Unified API

Base REST URL:

```text
https://api.tfl.gov.uk
```

Swagger/OpenAPI document:

```text
https://api.tfl.gov.uk/swagger/docs/v1
```

Authentication:

```text
Query parameter: app_key=<TFL_PRIMARY_KEY or TFL_SECONDARY_KEY>
```

TfL documentation says the Unified API provides highly requested realtime and status information across transport modes and that `app_key` should be appended as a query parameter.
