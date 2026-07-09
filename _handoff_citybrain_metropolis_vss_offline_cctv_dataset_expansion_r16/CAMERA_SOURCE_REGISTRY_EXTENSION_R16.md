# CAMERA / SOURCE REGISTRY EXTENSION — R16

Required fields:

```text
camera_source_id
dataset_id
source_type
fixed_camera_flag
video_or_frame_source
original_media_type
derived_media_type
license_status
attribution_required
geolocation_precision
timestamp_type
privacy_boundary
source_class_allowed
review_state
```

Allowed `source_type` values:

```text
fixed_cctv_image_replay
fixed_cctv_video_replay
dashcam_video_replay
surveillance_video_replay
synthetic_replay
```

Never use `live_cctv` unless a real live source exists.
