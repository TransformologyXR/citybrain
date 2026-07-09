# ACCEPTANCE CHECKS — R20

PASS requires:

- R19 package validates cleanly.
- Review packet emitted.
- Cockpit tile fixture emitted.
- Per-frame card fixtures emitted.
- False-positive and missed-annotation review lists emitted.
- Source classes preserved.
- No packaged media files unless explicitly selected.
- External media refs preserved.
- JSON/JSONL parse PASS.
- hash manifest PASS.
- audits PASS.
- no live CCTV claim.
- no action/finding/ticket/dispatch/identity/legal claim.

Partial if:

- R19 validates but app/cockpit fixture is contract-only.
- review packet emitted but no UI fixture.
- media refs unavailable but provenance retained.

Fail if:

- source classes collapse;
- DeepStream outputs are treated as findings;
- dataset annotations are treated as official truth;
- live CCTV is claimed;
- action/dispatch/ticket/legal/identity claim appears.
