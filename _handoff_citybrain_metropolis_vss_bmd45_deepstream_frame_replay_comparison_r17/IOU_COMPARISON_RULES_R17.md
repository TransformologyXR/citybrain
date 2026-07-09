# IOU COMPARISON RULES — R17

Use pixel-coordinate bounding boxes.

For each frame:

1. Convert both annotation and sensor detections into `[x, y, w, h]`.
2. Compute IoU for each annotation/detection pair.
3. Greedily match highest IoU pairs by class-family compatibility.
4. Report thresholds at 0.25 and 0.50.
5. Emit unmatched annotations and unmatched sensor detections.

This is review evidence, not model certification.
