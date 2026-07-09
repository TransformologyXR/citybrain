# PACKAGE CONTRACT — R17

Expected freeze package:

```text
METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_PACKAGE.zip
```

The package may be lightweight. Large images/videos should remain external media references unless explicitly requested.

## Required package sections

1. Input validation and lineage
2. Dataset media fetch/cache report
3. DeepStream replay input prep
4. DeepStream runtime execution report
5. Raw metadata and normalized candidate observations
6. Dataset annotation fixtures
7. Class mapping and IoU comparison
8. Human-review comparison packet
9. Final audits
10. Known limitations and next recommendations
11. Hash manifest

## Manifest rules

`HASH_MANIFEST.json.files` must include only files inside the ZIP.

External media must be listed under:

```json
"external_media_refs": []
```

with URL/path/bytes/SHA, and `packaged_file=false`.
