# Known Blockers / Caveats

## Sandbox validation

The ChatGPT sandbox could not resolve these hostnames:

- `datamall2.mytransport.sg`
- `api.tfl.gov.uk`

Therefore key validity was not confirmed here. This is an infrastructure/DNS limitation of the sandbox, not evidence that the keys are bad.

## LTA

- Standard DataMall REST endpoints should use the LTA DataMall API Account Key in the `AccountKey` request header.
- The Extended OBU SDK Account Key is tracked separately and should not be assumed valid for ordinary REST endpoints.
- Traffic image URLs may be short-lived; store metadata and evidence references, not heavy image payloads, unless a specific media acquisition task is opened.

## TfL

- TfL Unified API uses `app_key` as a query parameter.
- Request URLs must be sanitized before logging so `app_key` is never persisted.
- Primary key should be tried first; secondary key is fallback only.

## Product boundary

LTA/TfL feeds are transport context. They do not create dispatch, routing, enforcement, control, certified safety, or legal conclusions.
