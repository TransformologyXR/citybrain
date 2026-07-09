# IMPLEMENTATION NOTES — R17

## Static frame replay with DeepStream

DeepStream pipelines are commonly video/stream oriented. R17 can handle static frames by:

1. creating a short MP4/slideshow from the R16 BMD-45 image refs;
2. reading image sequence input where supported;
3. invoking a one-frame/per-image pipeline if available;
4. returning an honest partial if the container/source config cannot support still-frame replay.

## Comparison should not be accuracy certification

R17 is not certifying the model. It is proving that:

- a license-safe CCTV-like frame source can be replayed;
- actual DeepStream metadata can be compared to dataset annotations;
- source classes stay separated;
- review packets can show model output vs annotation evidence.

Low match rates are not automatically failure. Fabrication or boundary drift is failure.

## Class mapping

Use broad class-family mapping first:

```text
car / sedan / hatchback / SUV / van / bus / truck / two-wheeler / three-wheeler / unknown_vehicle
```

Record unmapped classes explicitly.
