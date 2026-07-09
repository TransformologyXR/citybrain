# CLASS MAPPING POLICY — R17

R17 compares two different label spaces:

- BMD-45 dataset annotations;
- DeepStream/Metropolis detector labels.

Do not require exact label-name equality. Emit both:

1. exact-class comparison where possible;
2. vehicle-family comparison for practical review.

Example mapping:

```json
{
  "BMD-45:Car": "vehicle_family:car",
  "BMD-45:Bus": "vehicle_family:bus",
  "BMD-45:Truck": "vehicle_family:truck",
  "BMD-45:Two-wheeler": "vehicle_family:two_wheeler",
  "BMD-45:Three-wheeler": "vehicle_family:three_wheeler",
  "DeepStream:car": "vehicle_family:car",
  "DeepStream:bicycle": "vehicle_family:two_wheeler",
  "DeepStream:motorbike": "vehicle_family:two_wheeler",
  "DeepStream:bus": "vehicle_family:bus",
  "DeepStream:truck": "vehicle_family:truck"
}
```

When unsure, map to `vehicle_family:unknown_vehicle` and keep the original label.
