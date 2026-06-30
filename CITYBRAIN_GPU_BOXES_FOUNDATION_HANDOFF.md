# CityBrain GPU Boxes Foundation Handoff

Generated: 2026-06-25

## Status

PASS. The laptop can SSH to both GPU boxes. Host GPU, Docker GPU, and role-specific services are verified. CityBrain processed data and current projection artifacts are synced to the RTX 3090. A real-data RAPIDS cuDF/cuGraph probe passed on the RTX 3090. The RTX 4070 face-layer foundation serves the app and status endpoints locally.

## Machine Roles

### RTX 3090

- Host alias: `txr-3090`
- IPv4: `192.168.1.148`
- Ubuntu user: `txr`
- Role: data / graph / RAPIDS / cuDF / cuGraph / cuSpatial / a4-D3b / later a6 optimization
- GPU: NVIDIA GeForce RTX 3090
- Data root: `/data/citybrain`

Verified components:

- SSH: PASS
- Host GPU via `nvidia-smi`: PASS
- Docker GPU via CUDA container: PASS
- Docker image `rapidsai/notebooks:26.06-cuda12-py3.11-amd64`: PASS
- Real CityBrain parquet read with cuDF: PASS
- D3a graph projection edge list loaded into cuGraph: PASS

Key paths:

- Processed data: `/data/citybrain/processed/`
- D3a snapshots: `/data/citybrain/a4d3a_snapshots/a4d3a_multidistrict_projection/`
- D2b discovery: `/data/citybrain/a4d2b_district_discovery/`
- D6b narration surface: `/data/citybrain/a5d6b_narration_surface/`
- Source scripts: `/data/citybrain/src/`
- RAPIDS work: `/data/citybrain/rapids_work/`
- Logs: `/data/citybrain/logs/` and `~/txr_setup_logs/`

Evidence logs:

- `~/txr_setup_logs/txr-3090-foundation-freeze.txt`
- `/data/citybrain/logs/txr-3090-foundation-freeze.txt`
- `~/txr_setup_logs/txr-3090-citybrain-sync-manifest.txt`
- `/data/citybrain/logs/txr-3090-citybrain-sync-manifest.txt`
- `~/txr_setup_logs/txr-3090-real-data-rapids-probe.txt`
- `/data/citybrain/logs/txr-3090-real-data-rapids-probe.txt`

RAPIDS probe result:

- `parquet_file_count: 868`
- First real parquet read: `/data/processed/nyc/harvest_v0_2/deduped_tables/nyc__building_energy_and_water_disclosure_ll84/part-00000.parquet`
- First parquet shape: `49465 x 271`
- Graph edge parquet: `/data/a4d3a_snapshots/a4d3a_multidistrict_projection/districts/1-01060/graph_projection_edges.parquet`
- Graph input rows: `2884`
- Encoded vertices: `2096`
- Degree rows: `2096`
- Final marker: `PASS_REAL_DATA_RAPIDS_PROBE`

### RTX 4070

- Host alias: `txr-4070`
- IPv4: `192.168.1.48`
- Ubuntu user: `txr`
- Role: face layer / dashboard / trace / briefing / later perception
- GPU: NVIDIA GeForce RTX 4070
- App root: `~/txr_workspace/citybrain-face`
- Deploy root: `/srv/citybrain/current`
- Data root: `/data/citybrain`

Verified components:

- SSH: PASS
- Host GPU via `nvidia-smi`: PASS
- Docker GPU via CUDA container: PASS
- Node: `v24.18.0`
- npm: `11.16.0`
- pnpm: `11.9.0`
- Caddy: `v2.11.4`
- Caddy localhost app: PASS
- Face-layer endpoints: PASS

Key paths:

- Face app source: `~/txr_workspace/citybrain-face`
- Caddy deploy root: `/srv/citybrain/current`
- Status endpoint file: `/srv/citybrain/current/status.json`
- Face-layer data root: `/data/citybrain`
- Receive path from 3090: `/data/citybrain/from_3090`
- Briefings: `/data/citybrain/briefings`
- Traces: `/data/citybrain/traces`
- Map tiles: `/data/citybrain/map_tiles`
- Logs: `/data/citybrain/logs/` and `~/txr_setup_logs/`

Evidence logs:

- `~/txr_setup_logs/txr-4070-foundation-freeze.txt`
- `/data/citybrain/logs/txr-4070-foundation-freeze.txt`
- `~/txr_setup_logs/txr-4070-face-layer-freeze.txt`
- `/data/citybrain/logs/txr-4070-face-layer-freeze.txt`

Face-layer endpoint results:

- `/`: `200`
- `/map`: `200`
- `/trace`: `200`
- `/briefing`: `200`
- `/status.json`: `200`

Status endpoint:

```json
{
  "host": "txr-4070",
  "role": "CityBrain face layer",
  "status": "foundation_ready",
  "surfaces": ["/map", "/trace", "/briefing"],
  "deferred": ["Triton", "Metropolis VSS", "Cosmos API clips", "Omniverse Kit Streaming"]
}
```

## Verification Commands

Foundation quick checks:

```bash
ssh txr-3090 "hostname; whoami; nvidia-smi -L; docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi | grep -E 'NVIDIA-SMI|RTX|3090'; docker images | grep -E 'rapids|cuda' || true"
ssh txr-4070 "hostname; whoami; nvidia-smi -L; docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi | grep -E 'NVIDIA-SMI|RTX|4070'; node --version; npm --version; caddy version; curl -I http://localhost:8080"
```

RAPIDS real-data probe:

```bash
ssh txr-3090 "docker run --rm --gpus all --user 0:0 -v /data/citybrain:/data rapidsai/notebooks:26.06-cuda12-py3.11-amd64 python /data/rapids_work/real_data_rapids_probe.py"
```

4070 face-layer status:

```bash
ssh txr-4070 "curl -sS http://localhost:8080/status.json"
```

## Synced CityBrain Data

Source on laptop:

```text
C:\Users\hazem\Documents\CityBrain
```

Synced to RTX 3090:

```text
/data/citybrain/processed/
/data/citybrain/a4d3a_snapshots/a4d3a_multidistrict_projection/
/data/citybrain/a4d2b_district_discovery/
/data/citybrain/a5d6b_narration_surface/
/data/citybrain/src/
```

Current 3090 size summary:

```text
144M  /data/citybrain/a4d2b_district_discovery
6.1M  /data/citybrain/a4d3a_snapshots
732K  /data/citybrain/a5d6b_narration_surface
3.4G  /data/citybrain/processed
712K  /data/citybrain/src
```

## Deferred Installs

These remain intentionally deferred:

- cuOpt: deferred until a6.
- Triton: deferred until a specific perception model exists.
- Metropolis VSS: deferred.
- Omniverse / Kit Streaming: deferred.
- NeMo and NIM on 3090/4070: deferred; those remain Spark/DGX responsibilities.
- Host-level PyTorch, conda, or ML libraries: not installed; ML/data stacks stay containerized.

## Known Caveats

- The RAPIDS probe was run as root inside the container to allow writing the mounted probe log. The probe script reads source data and writes only `/data/citybrain/logs/txr-3090-real-data-rapids-probe.txt`.
- The 4070 face-layer route paths currently return the existing app shell/placeholders. They are foundation endpoints, not final production UI surfaces.

## Next Recommended Workstream

1. Run a4-D3b district-scale GPU graph projection on the RTX 3090 using `/data/citybrain/processed` and `/data/citybrain/a4d3a_snapshots`.
2. Wire the RTX 4070 face layer to consume 3090-produced briefings and traces via `/data/citybrain/from_3090`, `/data/citybrain/briefings`, and `/data/citybrain/traces`.
3. Keep cuOpt deferred to a6.
4. Keep perception stack deferred until real perception input exists.
