# VSS SPARK COMMAND WRAPPER CONTRACT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

Command wrapper mode should be callable with input and output paths.

Recommended pattern:

```text
CITYBRAIN_SPARK_VSS_COMMAND="python /path/to/vss_wrapper.py --input-json {input_json} --output-json {output_json}"
```

The wrapper must:

- read a bounded JSON request
- write a bounded JSON response
- exit non-zero on failure
- not print secrets
- not mutate input files
- not write candidate event changes
- not create official records or actions
