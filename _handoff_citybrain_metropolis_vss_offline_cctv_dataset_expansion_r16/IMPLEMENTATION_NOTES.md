# IMPLEMENTATION NOTES — R16

Practical path:
1. Parse the candidate matrix.
2. Select BMD-45 by default unless a stronger video dataset has license gate PASS.
3. Create a bounded sample manifest.
4. Record license and attribution.
5. Build external media refs rather than packaging large media.
6. Emit camera/source registry entries.
7. Emit candidate observation fixture only from actual annotations/metadata, or mark as synthetic fixture.
8. Run audits.

Suggested next after R16:
- R17: process selected dataset sample through DeepStream/Metropolis.
- R18: join VSS narration over selected replay subset.
- R19: human-review UI packet using real offline dataset samples.
