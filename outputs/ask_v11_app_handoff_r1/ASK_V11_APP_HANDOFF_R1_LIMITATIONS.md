# ASK v1.1 App Handoff R1 Limitations

- R1 is local/demo web-control-room handoff only.
- The Kit extension is not wired to ASK v1.1 handoff fixtures in this package.
- The handoff fixture file is loaded from `outputs/ask_v11_app_handoff_preflight/ASK_V11_APP_HANDOFF_FIXTURES.json`; if that file is absent, the ASK handoff panel is simply not rendered.
- The fixtures remain `app_handoff_fixture` payloads. They are not retained source truth.
- No production ASK API, live request path, or app-to-ASK runtime invocation was added.
- No citation URL fetch was added; source URI fields are display-only when present.
- Real-corpus contradiction remains waived for R2 until a valid retained same-claim contradiction pair appears.
- The existing `apps/` tree is untracked in this workspace, so a commit package must stage only the intended R1 app files.
