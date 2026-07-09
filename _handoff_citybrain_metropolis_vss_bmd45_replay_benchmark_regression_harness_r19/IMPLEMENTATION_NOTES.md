# IMPLEMENTATION NOTES — R19

Recommended approach:

1. Reuse the R18 external-media fixture set as the first fixed benchmark.
2. Treat the R18 numbers as baseline measurements, not product-quality claims.
3. Make regression assertions tolerant enough to catch broken pipeline behavior without pretending model output should be perfectly deterministic.
4. Suggested hard checks:
   - external media refs count remains 8 unless benchmark version changes
   - source classes remain correct
   - DeepStream execution status is either `EXECUTED_SUCCESS` or a documented partial
   - candidate count is nonzero if rerun executes
   - no action/official/identity/legal terms appear in outputs
5. Suggested soft drift checks:
   - candidate count within configurable tolerance band of 165
   - IoU 0.25 matches within configurable tolerance band of 24
   - IoU 0.5 matches within configurable tolerance band of 19
   - confidence distribution remains plausible

Do not modify `requirements.txt` solely because pytest is installed locally; record it as environment state if used.
