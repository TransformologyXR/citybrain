# R10 — DeepStream Evidence Frame / Clip Export

## Goal

Attach visible media evidence to the R2/R8 candidate event.

## Minimum viable output

One of:

1. representative frame image + bbox metadata, or
2. bounded clip reference with frame/time start/end.

## Recommended implementation

- Read R2/R8 candidate event metadata.
- Select representative observation(s), preferably highest confidence or median frame.
- Use ffmpeg/OpenCV/GStreamer to extract one frame from the source video.
- If bbox metadata exists, emit overlay metadata; visual overlay is optional.
- Hash exported frame/clip.
- Add frame/clip ref to EvidenceBundle and human-review packet.

## PASS criteria

- frame or clip reference exists
- media file hash recorded
- frame/time ref recorded
- candidate event unchanged
- no official/action claim
