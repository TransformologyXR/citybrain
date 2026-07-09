# Known blockers

- Direct downloads were not executed here because the local container has no DNS.
- OpenAQ API v3 expects `X-API-Key`.
- TfL requires an app key for product use.
- LTA DataMall requires an AccountKey; previous scouts hit 401.
- CDS ERA5 needs CDSAPI token/config.
- DLD current-year web export has date filters/captcha; previous-year data points to Dubai Pulse.
- GeoDubai official geospatial layers may require request/access workflow.
- Large sources such as Geofabrik, JRC GSW, and OPSD should not be pulled into the repo.
