# ROADMAP — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH

## Sprint theme

```text
From functional proof to usable review cockpit
```

## Baseline

R5 is closed:

```text
PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS
```

R5 proved live WebRTC stream, real Barcelona scene references, scene prim selection parity, event overlay parity, object-event review loop, packet truth, and no-action boundary.

## R6 sequence

### 1. Side rail / collapsible overlay

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-SIDE-RAIL-COLLAPSIBLE-OVERLAY
```

Acceptance:

- Inspector no longer blocks the main stream.
- Expanded/collapsed states work.
- Selected object/event state is preserved across collapse.
- Packet truth remains visible when expanded.

### 2. Better inspector layout

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-INSPECTOR-LAYOUT-POLISH
```

Acceptance:

- Inspector has clear sections: Summary, Evidence, Limitations, Does not prove, Review state, No action, Source refs/packet hash.
- Object and event views are visually distinct.
- Empty/no-selection state exists.
- Candidate/review-only labels are visible.

### 3. Operator workflow states

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-OPERATOR-WORKFLOW-STATES
```

Acceptance:

- Local states work: hold, needs_source, reviewed, abstain, note_added, clear/reset.
- State changes are local review state only.
- No official ticket/case/action is created.
- State transition log is captured.

### 4. Review notes and export UX

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-REVIEW-NOTE-EXPORT-UX
```

Acceptance:

- Operator can add a note.
- Local review packet export works as JSON.
- Optional Markdown export if feasible.
- Export includes evidence refs, limitations, no-action state, selected prim/event, and packet hash.
- Export clearly says review-only / not_executed.

### 5. Real authored scene polish

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-AUTHORED-SCENE-POLISH
```

Acceptance:

- Visual readability improves.
- Labels/bookmarks/camera presets are cleaner.
- Marker clutter is reduced.
- Materials/markers are consistent without implying official status.
- Real scene refs and review-anchor caveat are preserved.

### 6. Regression and close

Task:

```text
MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-CLOSEOUT
```

Acceptance:

- R5 object/event parity still passes.
- One-truth packet audit passes.
- Boundary audit passes.
- Full discovery passes.
- Hash manifest verifies.

## Recommended execution order

```text
1. Side rail / collapsible overlay
2. Inspector layout polish
3. Workflow states
4. Notes/export UX
5. Scene polish
6. Regression + close
```

Scene polish can run in parallel if someone is working in Kit/USD while another person handles WebUI.

## Stop line

Do not add:

- production WebRTC
- public/cloud streaming
- OKAS/GDN
- auth/RBAC
- latency/SLA
- perception/VSS/Metropolis/DeepStream
- official case/ticket integration
- automated action
- legal/certified findings
