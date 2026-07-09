# Implementation Notes

## R9 input

Use R9 as the source of truth. Do not re-open R7/R8 unless package validation fails.

## Media handling

Prefer references and hashes over embedding large media in the ZIP. If a frame is small, it may be included. If a clip is large, include manifest and hash.

## RTSP simulation

Acceptable implementations include:
- file input only with stable source registry
- ffmpeg loop to RTSP service
- GStreamer RTSP server
- MediaMTX / rtsp-simple-server style local service

Do not store camera credentials.

## External dataset

Do not download or package external video until license/terms are recorded.

## Tests

Add targeted tests for:
- frame manifest creation
- replay source manifest
- zone membership
- no synthetic class invention
- UI packet required fields
- camera/source registry required fields
- final audits
