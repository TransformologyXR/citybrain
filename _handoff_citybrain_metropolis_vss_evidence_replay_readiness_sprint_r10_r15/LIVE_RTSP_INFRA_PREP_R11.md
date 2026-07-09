# R11 — Live / RTSP Infrastructure Prep with Offline Replay

## Goal

Prepare for a future real CCTV/RTSP camera while using offline replay now.

## Options

### Option A — file replay only

Use local file input with a stable `media_source_id`.

### Option B — file-to-RTSP simulation

Use ffmpeg/GStreamer/MediaMTX or equivalent to expose the offline video as an RTSP stream.

### Option C — future real camera contract

Do not connect to real CCTV yet. Emit contract fields:
- camera_id
- rtsp_url_placeholder
- credentials_secret_ref
- timezone
- location
- consent/privacy status
- retention policy
- source owner

## PASS criteria

- offline replay works or is declared file-mode PASS
- future RTSP contract exists
- no camera credentials stored in package
- source registry links replay source to candidate event
