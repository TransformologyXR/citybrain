# BMD-45 FRAME REPLAY PLAN — R16

BMD-45 is the preferred first dataset for R16 because it is fixed CCTV traffic imagery and has explicit `cc-by-4.0` license metadata on Hugging Face.

Use pattern:

```text
BMD-45 sample images
→ frame-replay manifest
→ camera/source registry entries
→ media provenance
→ DeepStream/Metropolis compatibility fixture
→ candidate observation fixture
```

Important limitation: BMD-45 is image/frame based, not a continuous video source. If images are rendered into a short MP4 for replay, the generated MP4 must be labelled `derived_frame_replay_clip`, `not_live_cctv`, and `not_original_video`.

Minimum sample: 25-100 images.
