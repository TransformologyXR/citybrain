# CityBrain Metropolis/VSS Spark split-host readiness R6D

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D`

Purpose: prepare the integration contract while VSS is being installed on Spark.

This is not a VSS narration run. It is a split-host readiness package that locks the current host allocation and prepares the bridge between:

- DeepStream / Metropolis on `txr-4070`
- VSS on Spark / DGX Spark once installed and configured
- `txr-3090` as not active for the current Metropolis/VSS chain

R7 remains blocked until a real Spark VSS command or endpoint passes the connectivity/readiness gate.
