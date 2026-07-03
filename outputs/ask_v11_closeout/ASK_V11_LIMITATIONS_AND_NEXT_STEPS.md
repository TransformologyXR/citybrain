# ASK v1.1 Limitations And Next Steps

## Non-Claims And Limitations

- Fixture/local evidence only.
- No live or production retrieval.
- No production API.
- No official action, ticket creation, dispatch, routing, control, or enforcement.
- No autonomous workflow.
- No legal, certified, final, or official determination claim.
- No WATCH runtime.
- No BRIEF runtime.
- No DIFF runtime.
- No INCIDENT runtime.
- No live model required.
- Future flows are skeleton-only.
- Sealed eval is local fixture-based.
- The broader dirty worktree pre-existed this sprint and was not cleaned or reverted.

## What May Happen Next

Recommended default:

```text
ASK-V11-REPO-COMMIT-AND-PR-PREP
```

Purpose: commit clean ASK v1.1 scope and prepare a PR.

Other valid next packages:

```text
ASK-V11-REAL-CORPUS-EVAL-PREFLIGHT
```

Purpose: map sealed fixture eval to real retained ASK corpus without changing runtime.

```text
ASK-V11-APP-HANDOFF-PREFLIGHT
```

Purpose: expose sealed ASK packets to cockpit UI as local/demo integration.

```text
WATCH/BRIEF/DIFF/INCIDENT DESIGN ONLY
```

Purpose: expand skeleton contract tests only after freeze, with no runtime.

## What Must Not Happen As The Immediate Next Step

- Do not implement a P5 runtime package.
- Do not add WATCH/BRIEF/DIFF/INCIDENT runtime.
- Do not add live retrieval or production adapters.
- Do not add official action, ticket, dispatch, routing, control, or enforcement behavior.
- Do not widen G1/G2/G3 taxonomy without a real Sev-4 eval family.
