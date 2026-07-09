# IMPLEMENTATION NOTES — R7

## Endpoint mode

R6C proved `/v1/ready`. R7 needs an actual narration/summarization route or a command wrapper.
If the only endpoint configured is `/v1/ready`, return partial.

Use one of:

```text
CITYBRAIN_SPARK_VSS_SUMMARIZE_ENDPOINT=http://spark-2445:38111/v1/summarize
CITYBRAIN_SPARK_VSS_COMMAND=/path/to/citybrain_vss_summarize_wrapper.sh
```

Confirm the route against the installed VSS profile. Do not assume a request schema if the
service returns a client error. Capture the redacted response and return partial if needed.

## Command-wrapper mode

The wrapper should receive a media path and optional prompt/context JSON and return JSON to stdout.

Suggested stdout:

```json
{
  "status": "success",
  "summary": "...",
  "events": [
    {"time_ref": "frame_or_time", "description": "..."}
  ],
  "model": "configured_by_runtime",
  "source_class": "model_generated_narrative"
}
```

## Prompt for VSS

Use bounded phrasing:

```text
Summarize only what is visible in this media sample. Do not identify people.
Do not infer legal violations. Do not create instructions. Treat this as candidate
review context only. Note uncertainty.
```

## Secret handling

Do not include NVIDIA API keys, Authorization headers, cookies, or bearer tokens in any artifact.
Redact headers and environment dumps.
