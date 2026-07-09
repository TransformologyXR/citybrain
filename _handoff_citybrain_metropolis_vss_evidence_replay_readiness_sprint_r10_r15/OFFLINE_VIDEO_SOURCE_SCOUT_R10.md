# Offline Video Source Scout — R10

## Purpose

Find a safe offline video source to simulate CCTV/live camera behavior until a real CCTV feed exists.

## Source candidates

### Candidate A — Existing DeepStream SDK sample media

Use first because it is already present locally and was proven in R2.

Known file:

```text
samples/streams/sample_1080p_h264.mp4
```

Strengths:
- Already proven with DeepStream metadata export.
- No download dependency.
- Best for deterministic regression.

Limitations:
- Not a real city CCTV feed.
- Limited scene diversity.
- Prior R2 selected car records only.

### Candidate B — AI City Challenge / CityFlowV2

Use if download and license review are acceptable.

Strengths:
- CCTV-like traffic camera data.
- Multi-camera, multi-intersection vehicle data.
- Better fit for multi-zone / multi-source replay.

Acceptance before use:
- Record dataset URL.
- Record license/terms.
- Record selected file hash.
- Use only a small representative clip for bounded review.

### Candidate C — AI City WTS traffic-safety videos

Use if the goal is richer VSS narration behavior.

Strengths:
- Designed for traffic safety description/captioning.
- High-resolution videos and manual captions.
- Better stress test for VSS narrative context.

Acceptance before use:
- Verify download terms.
- Do not treat annotations as official truth.
- Keep all outputs as review-only.

### Candidate D — VIRAT-like surveillance data

Only use if license/source authenticity can be verified.

Do not use Kaggle mirrors or third-party rehosts as authoritative without license review.

## Selection policy

The sprint may PASS with Candidate A alone if frame/clip export, replay infrastructure, UI packet, registry, provenance, and audits pass.

External video is a bonus, not a blocker.
