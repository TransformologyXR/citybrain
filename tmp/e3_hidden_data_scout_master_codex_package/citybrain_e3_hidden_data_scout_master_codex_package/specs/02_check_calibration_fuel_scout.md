# Lane B — CHECK Calibration Fuel Scout

Find historical CHECK signals and later outcomes/resolution evidence.

## Target join pattern

```text
CheckReport / CheckResult
→ subject or watch_item_id / evidence_ref / source_ref
→ later OutcomeRecord / ReviewState / Brief / Decision
```

## Required reports

- counts by check type
- counts by source_class
- counts by Watch family
- counts by domain pack
- confirmed/dismissed/needs_more/held/unresolved breakdown
- unresolved contradictions and stale-source examples
