# IMPLEMENTATION NOTES — R6E

Use this task to remove ambiguity for the Spark install team.

Recommended operational sequence:

1. Confirm Spark host reachable from orchestration environment.
2. Confirm VSS service/process exists on Spark.
3. Expose either a local command wrapper or HTTP endpoint.
4. Validate with a harmless health/version probe first.
5. Validate with a bounded sample payload that references R2 evidence IDs only.
6. Redact all tokens/paths/secrets from package artifacts.
7. Set `r7_ready=true` only after successful probe.

Do not run R7 narration smoke until R6E/R6D connectivity returns SUCCESS.
