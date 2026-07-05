const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export const DEFAULT_WEBRTC_CONFIG = Object.freeze({
  schema_version: "citybrain.omniverse.webrtc.local_dev_config.r1",
  task_id: "MAIN-CITYBRAIN-OMNIVERSE-NATIVE-KIT-SPATIAL-COCKPIT-UI-R3-WEBRTC-LIVE-WEBUI-BRIDGE",
  profile: "local_dev_only",
  kit_application: "CityBrain USD Composer",
  kit_extensions: [
    "citybrain.control_room",
    "omni.kit.livestream.app",
    "omni.kit.livestream.webrtc",
    "omni.services.livestream.webrtc"
  ],
  web_sdk_entrypoint: "AppStreamer",
  signaling_url: "ws://127.0.0.1:49100",
  session_service_url: "http://127.0.0.1:8011",
  stream_port: 47998,
  signal_port: 49100,
  local_only: true,
  pixel_truth_boundary: "streamed_pixels_are_not_citybrain_evidence_or_action_truth",
  packet_truth_root: "packages/fixtures/mobility_access/runtime_bundle",
  packet_truth_rule: "packets remain the source of truth",
  no_action_state: "not_executed"
});

export const CITYBRAIN_WEBRTC_MESSAGE_CONTRACTS = Object.freeze({
  schema_version: "citybrain.omniverse.webrtc.message_contracts.r1",
  allowed_outbound_types: [
    "citybrain.selection.focus_request",
    "citybrain.event.focus_request"
  ],
  allowed_inbound_types: [
    "citybrain.selection.changed",
    "citybrain.event.selection_changed",
    "citybrain.event.overlay_upsert",
    "citybrain.stream.state"
  ],
  rejected_action_like_types: [
    "citybrain.action.execute",
    "citybrain.dispatch.request",
    "citybrain.enforcement.create",
    "citybrain.case.create",
    "citybrain.alert.publish",
    "citybrain.legal.certify"
  ],
  execution_state: "not_executed",
  no_action_taken: true
});

export const CITYBRAIN_R6_WORKFLOW_STATES = Object.freeze([
  "hold",
  "needs_source",
  "reviewed",
  "abstain",
  "note_added",
  "cleared/reset"
]);

const NO_ACTION_CANNOT_CLAIM = Object.freeze([
  "not a certified physical twin",
  "not measurement-grade geometry",
  "not an official affected asset/building determination",
  "not live monitoring",
  "not dispatch, routing/control, enforcement, ticket/case creation, or automated action",
  "not a legal/certified finding"
]);

const EVENT_REVIEW_PACKETS = Object.freeze([
  {
    event_id: "event:replay:blockage:001",
    event_label: "Replay blockage marker",
    event_type: "replay_blockage_marker",
    canonical_entity_id: "scene_prim:corridor:blocked-lane-zone",
    target_prim_path: "/CityBrainBrowserNavTest/BlockedLaneZone",
    marker_prim_path: "/CityBrainR4EventOverlays/ReplayBlockage001",
    evidence_refs: ["event:replay:blockage:001", "scene_prim:corridor:blocked-lane-zone", "d7_candidate_observation:003"],
    limitation_refs: ["limitation:local_replay_only", "stream is visual context only; event truth is packet-driven", "replay event marker; not live monitoring"],
    packet_hash: "f307ebab7da162a3612b42030342d19cbf07d1313d64fd774e76203877fab2ec"
  },
  {
    event_id: "event:replay:evidence:001",
    event_label: "Evidence-linked D7 marker",
    event_type: "evidence_linked_marker",
    canonical_entity_id: "scene_prim:evidence:d7-observations-pin",
    target_prim_path: "/CityBrainBrowserNavTest/EvidencePinD7Observations",
    marker_prim_path: "/CityBrainR4EventOverlays/EvidenceD7Marker001",
    evidence_refs: ["event:replay:evidence:001", "d7_candidate_observation:001", "d7_candidate_observation:002"],
    limitation_refs: ["limitation:local_replay_only", "candidate observations remain review context", "not a legal/certified finding"],
    packet_hash: "5d2d46b0837cabdc1ef99ba574fdf1fc8d232fc1caa776cfd7b79366bb09bca4"
  },
  {
    event_id: "event:replay:limitation:001",
    event_label: "Limitation review marker",
    event_type: "limitation_marker",
    canonical_entity_id: "scene_prim:barcelona_review:review-marker-001",
    target_prim_path: "/CityBrainR5RealSceneReviewLoop/BarcelonaReviewBoundaryMarker001",
    marker_prim_path: "/CityBrainR4EventOverlays/LimitationMarker001",
    evidence_refs: ["event:replay:limitation:001", "limitation:local_replay_only"],
    limitation_refs: ["limitation:local_replay_only", "selected prim is not an official affected asset/building determination"],
    packet_hash: "ffb3f72f2b5a8129b05cff76d9eb3e23eb62cdcc92449e8bb2bc0dcd5f126003"
  }
]);

const WORKFLOW_STORAGE_KEY = "citybrain.omniverse.r6.operatorWorkflow";
const WORKFLOW_TRANSITION_KEY = "citybrain.omniverse.r6.operatorWorkflow.transitions";
const WORKFLOW_EXPORT_KEY = "citybrain.omniverse.r6.operatorWorkflow.exports";

function dataJson(value) {
  return esc(JSON.stringify(value ?? null));
}

function readJson(value, fallback) {
  try {
    return JSON.parse(value || "");
  } catch {
    return fallback;
  }
}

function overlayRows(bundle) {
  return bundle?.overlays?.packets
    || bundle?.kitOverlay?.packets
    || bundle?.kitOverlay?.overlays
    || [];
}

function overlayForEntity(bundle, entityRef) {
  return overlayRows(bundle).find((row) => row.entity_ref === entityRef) || overlayRows(bundle)[0] || {};
}

function firstOverlay(bundle) {
  return overlayRows(bundle)[0] || {};
}

function entityTypeFromRef(entityRef) {
  const parts = String(entityRef || "").split(":");
  return parts.length >= 2 ? parts[parts.length - 2] : "unknown";
}

function entityLabelFromRef(entityRef) {
  const parts = String(entityRef || "").split(":");
  if (parts.length >= 3) {
    const kind = parts[parts.length - 2].replace(/_/g, " ");
    const name = parts[parts.length - 1].replace(/[-_]/g, " ");
    return `${kind}: ${name}`;
  }
  return String(entityRef || "unknown entity").replace(/[-_]/g, " ");
}

function selectedEntity(bundle, entityRefValue = "") {
  const overlay = entityRefValue ? overlayForEntity(bundle, entityRefValue) : firstOverlay(bundle);
  const entityRef = overlay.entity_ref || "mobility_access:cascade_context:hero-cross-domain";
  return {
    entity_ref: entityRef,
    entity_type: entityTypeFromRef(entityRef),
    entity_label: entityLabelFromRef(entityRef),
    prim_path: overlay.prim_path || "/CityBrain/MobilityAccess/mobility_access_cascade_context_hero_cross_domain",
    overlay_state: overlay.overlay_state || "review_context",
    claim_label: overlay.claim_label || "not_executed",
    limitation_ref: overlay.limitation_ref || "limitation:local_replay_only"
  };
}

function sourceRecords(bundle, entityRef) {
  const evidence = bundle?.evidence || {};
  return [
    entityRef,
    ...(evidence.candidate_observation_refs || []),
    ...(evidence.similar_case_refs || []),
    ...(evidence.cascade_refs || [])
  ].filter(Boolean);
}

function limitationRefs(bundle, entity) {
  const refs = [];
  if (entity.limitation_ref) refs.push(entity.limitation_ref);
  if (entity.limitation_ref) refs.push(`Selected overlay limitation ref: ${entity.limitation_ref}`);
  refs.push(...(bundle?.limitations?.limitations || []));
  return refs.filter(Boolean);
}

function canonicalStringify(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalStringify).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256Hex(payload) {
  const body = canonicalStringify(payload);
  const subtle = globalThis.crypto?.subtle;
  if (!subtle || typeof TextEncoder === "undefined") {
    return `sha256_unavailable_${body.length}`;
  }
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(body));
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function selectionPacketFromEntity(bundle, entityRef) {
  const entity = selectedEntity(bundle, entityRef);
  const review = bundle?.review || {};
  const oneTruth = bundle?.oneTruth || bundle?.one_truth || {};
  const trackD = bundle?.trackD || bundle?.track_d || {};
  return {
    schema_version: "citybrain.omniverse.selection_packet.canonical.r1",
    canonical_entity_id: entity.entity_ref,
    entity_type: entity.entity_type,
    entity_label: entity.entity_label,
    prim_path: entity.prim_path,
    evidence_refs: sourceRecords(bundle, entity.entity_ref),
    limitation_refs: limitationRefs(bundle, entity),
    review_state: {
      review_state_ref: review.review_state_ref || oneTruth.review_state_ref || "review_state:mobility-access:not_executed",
      track_d_authoritative: review.track_d_authoritative ?? true,
      approved_proposal_created: review.approved_proposal_created ?? false,
      execution_authority_created: review.execution_authority_created ?? false
    },
    no_action_state: {
      no_action_taken: true,
      execution_state: oneTruth.execution_state || review.execution_state || "not_executed",
      approved_proposal_created: trackD.approved_proposal_created ?? false,
      execution_authority_created: review.execution_authority_created ?? false
    },
    cannot_claim: [...NO_ACTION_CANNOT_CLAIM]
  };
}

function eventPacketFromEvent(event) {
  return {
    schema_version: "citybrain.omniverse.event_packet.canonical.r6",
    event_id: event.event_id,
    event_type: event.event_type,
    event_label: event.event_label,
    canonical_entity_id: event.canonical_entity_id,
    entity_label: entityLabelFromRef(event.canonical_entity_id),
    target_prim_path: event.target_prim_path,
    marker_prim_path: event.marker_prim_path,
    evidence_refs: [...event.evidence_refs],
    limitation_refs: [...event.limitation_refs],
    review_state: {
      review_state_ref: "review_state:event-overlay:needs_review",
      review_state: "needs_review",
      approved_proposal_created: false,
      execution_authority_created: false
    },
    no_action_state: {
      no_action_taken: true,
      execution_state: "not_executed",
      approved_proposal_created: false,
      execution_authority_created: false
    },
    cannot_claim: [...NO_ACTION_CANNOT_CLAIM],
    packet_hash: event.packet_hash,
    review_only: true,
    stream_visual_context_only: true,
    pixel_derived_truth_used: false
  };
}

function sourceRows(bundle) {
  const roots = [];
  const seen = new Set();
  for (const packetName of ["oneTruth", "evidence", "review", "limitations", "trackD", "kitOverlay"]) {
    for (const ref of bundle?.[packetName]?.source_root_refs || []) {
      const key = ref.key || ref.root || ref.path;
      if (!key || seen.has(key)) continue;
      roots.push(ref);
      seen.add(key);
    }
  }
  return roots.slice(0, 6);
}

function compactList(items, fallback) {
  const rows = (items || []).filter(Boolean);
  if (!rows.length) return `<li>${esc(fallback)}</li>`;
  return rows.map((item) => `<li>${esc(item)}</li>`).join("");
}

function buttonTextState(state) {
  if (state === "needs_source") return "Needs source";
  if (state === "note_added") return "Note added";
  if (state === "cleared/reset") return "Clear/reset";
  return state.replace(/_/g, " ").replace(/^\w/, (char) => char.toUpperCase());
}

function sectionList(items, fallback) {
  return `<ul class="plain-list compact">${compactList(items, fallback)}</ul>`;
}

export function classifyWebRtcMessage(message = {}) {
  const type = String(message.type || message.message_type || "");
  const actionLike = CITYBRAIN_WEBRTC_MESSAGE_CONTRACTS.rejected_action_like_types.includes(type)
    || /execute|dispatch|enforce|approve|case|ticket|alert|certify|legal|control/i.test(type);
  if (actionLike) {
    return {
      type,
      status: "REJECTED",
      reason: "review_only_no_action_boundary",
      execution_state: "not_executed",
      no_action_taken: true
    };
  }
  if (CITYBRAIN_WEBRTC_MESSAGE_CONTRACTS.allowed_outbound_types.includes(type) || CITYBRAIN_WEBRTC_MESSAGE_CONTRACTS.allowed_inbound_types.includes(type)) {
    return {
      type,
      status: "ACCEPTED_REVIEW_ONLY",
      execution_state: "not_executed",
      no_action_taken: true
    };
  }
  return {
    type: type || "unknown",
    status: "REJECTED",
    reason: "unsupported_message_type",
    execution_state: "not_executed",
    no_action_taken: true
  };
}

export function renderOmniverseStreamPanel(bundle) {
  const entity = selectedEntity(bundle);
  const packet = selectionPacketFromEntity(bundle, entity.entity_ref);
  const selectableEntities = overlayRows(bundle).slice(0, 7);
  const citations = sourceRows(bundle);
  const limitations = bundle?.limitations?.limitations || [];
  const evidence = bundle?.evidence || {};
  const scenario = bundle?.scenario || {};
  const review = bundle?.review || {};
  const firstEvent = eventPacketFromEvent(EVENT_REVIEW_PACKETS[0]);
  const sourceRefText = citations.length ? citations.map((ref) => esc(ref.key || ref.root || ref.path)).join(", ") : "No source refs loaded";
  return `<section id="omniverse-webrtc-bridge" class="panel span-12 omniverse-stream-panel" data-omniverse-webrtc-bridge="local-dev" data-r6-ui-ux-operator-workflow="true" data-stream-status="not_initialized" data-inspector-collapsible-state="expanded" data-selected-kind="object" data-local-review-state="hold" data-packet-truth-root="${esc(DEFAULT_WEBRTC_CONFIG.packet_truth_root)}" data-selected-entity-ref="${esc(entity.entity_ref)}" data-selected-entity-type="${esc(entity.entity_type)}" data-selected-prim-path="${esc(entity.prim_path)}" data-selected-event-id="" data-selected-event-marker-path="" data-evidence-refs="${dataJson(packet.evidence_refs)}" data-limitation-refs="${dataJson(packet.limitation_refs)}" data-review-state="${dataJson(packet.review_state)}" data-no-action-state="${dataJson(packet.no_action_state)}" data-cannot-claim="${dataJson(packet.cannot_claim)}" data-packet-hash="pending" data-selection-source="web_ui_initial_packet" data-execution-state="not_executed">
    <div class="stream-copy">
      <p class="section-kicker">Omniverse stream bridge</p>
      <h2>Local Kit viewport with a packet-backed operator rail</h2>
      <p class="human-explain">The streamed scene is visual context only. Object identity, event state, evidence, limitations, review state, notes, and no-action state are driven by CityBrain packets and local review state.</p>
      <div class="plain-status-row">
        <span id="omniverse-webrtc-session-state" class="status-pill">WebRTC: not initialized</span>
        <span class="status-pill safe">Local/dev only</span>
        <span class="status-pill safe">Review only</span>
        <span class="status-pill safe">Actions: not_executed</span>
        <span class="status-pill">Scenario: ${esc(scenario.scenario_id || scenario.scenario_state_ref || "mobility access review")}</span>
      </div>
    </div>
    <div class="stream-shell" data-side-rail-layout="collapsible">
      <main class="stream-stage" aria-label="Local Kit stream visual context">
        <div class="stream-toolbar" aria-label="Scene bookmarks and selected packet controls">
          <button type="button" data-webrtc-command="connect">Connect local stream</button>
          <button type="button" data-scene-bookmark="overview" data-webrtc-command="bookmark">Overview</button>
          <button type="button" data-scene-bookmark="object" data-webrtc-command="bookmark">Frame object</button>
          <button type="button" data-scene-bookmark="event" data-webrtc-command="bookmark">Frame event</button>
          <button type="button" data-side-rail-toggle="true" aria-controls="citybrain-operator-side-rail" aria-expanded="true">Collapse inspector</button>
        </div>
        <div id="omniverse-webrtc-stream-container" class="stream-container" aria-live="polite">
          <video id="omniverse-webrtc-remote-video" class="stream-video" autoplay playsinline muted></video>
          <div id="omniverse-webrtc-stream-placeholder" class="stream-placeholder">
            <strong>Waiting for local Kit WebRTC session</strong>
            <span id="omniverse-webrtc-stream-detail">No browser stream evidence is asserted until AppStreamer connects to a local Kit livestream endpoint.</span>
          </div>
          <div class="scene-polish-overlay" data-scene-polish="labels-bookmarks-marker-readability">
            <span data-scene-label="barcelona-real-scene">Barcelona/NYC real-scene review anchors</span>
            <span data-scene-label="packet-truth">Packets are truth</span>
            <span data-scene-label="not-official-asset">Not an official affected asset</span>
          </div>
        </div>
        <div class="stream-object-event-controls" aria-label="Packet-backed object and event controls">
          <div>
            <strong>Objects</strong>
            <div class="operator-actions">
              ${selectableEntities.map((row) => `<button type="button" data-webrtc-select-entity="true" data-entity-ref="${esc(row.entity_ref)}" data-entity-type="${esc(entityTypeFromRef(row.entity_ref))}" data-prim-path="${esc(row.prim_path)}">${esc(entityLabelFromRef(row.entity_ref))}</button>`).join("")}
            </div>
          </div>
          <div>
            <strong>Events</strong>
            <div class="operator-actions">
              ${EVENT_REVIEW_PACKETS.map((row) => `<button type="button" data-webrtc-select-event="true" data-event-id="${esc(row.event_id)}" data-event-label="${esc(row.event_label)}" data-target-prim-path="${esc(row.target_prim_path)}" data-marker-prim-path="${esc(row.marker_prim_path)}" data-event-packet="${dataJson(eventPacketFromEvent(row))}">${esc(row.event_label)}</button>`).join("")}
            </div>
          </div>
        </div>
      </main>
      <aside id="citybrain-operator-side-rail" class="stream-side-rail" data-side-rail-state="expanded" aria-label="Packet-backed object and event inspector">
        <div class="rail-header">
          <div>
            <p class="record-type">Packet-backed inspector</p>
            <h3 id="citybrain-selected-entity-title">${esc(entity.entity_label)}</h3>
          </div>
          <button type="button" data-side-rail-toggle="true" aria-controls="citybrain-operator-side-rail" aria-expanded="true">Collapse</button>
        </div>
        <section class="inspector-section empty-selection-state" data-inspector-section="empty-selection">
          <strong>No selection fallback</strong>
          <span>If Kit and WebUI have no selected object or event, this rail stays open and shows review-only packet boundaries instead of deriving truth from pixels.</span>
        </section>
        <section class="inspector-section" data-inspector-section="summary">
          <h4>Summary</h4>
          <dl class="operator-fields">
            <div><dt>Selected object/event</dt><dd id="citybrain-selected-entity-ref">${esc(entity.entity_ref)}</dd></div>
            <div><dt>Canonical ID</dt><dd id="citybrain-selected-canonical-id">${esc(entity.entity_ref)}</dd></div>
            <div><dt>Prim or marker path</dt><dd id="citybrain-selected-prim-path">${esc(entity.prim_path)}</dd></div>
            <div><dt>Overlay state</dt><dd id="citybrain-selected-overlay-state">${esc(entity.overlay_state)} | ${esc(entity.claim_label)} | ${esc(entity.limitation_ref)}</dd></div>
          </dl>
        </section>
        <section class="inspector-section" data-inspector-section="evidence">
          <h4>Evidence</h4>
          <p id="citybrain-selected-evidence">${esc(evidence.candidate_observation_count || 0)} candidate observations, ${esc(evidence.similar_case_count || 0)} similar cases, ${esc(evidence.cascade_attachment_count || 0)} cascade attachments | refs=${esc(packet.evidence_refs.length)}</p>
          ${sectionList(packet.evidence_refs.slice(0, 6), "No evidence refs loaded.")}
        </section>
        <section class="inspector-section" data-inspector-section="limitations">
          <h4>Limitations</h4>
          <p id="citybrain-selected-limitations">${esc(packet.limitation_refs.slice(0, 3).join(" | "))}</p>
          ${sectionList(limitations.slice(0, 4), "Local replay only; no certified or live operational finding.")}
        </section>
        <section class="inspector-section" data-inspector-section="does-not-prove">
          <h4>Does not prove</h4>
          <p id="citybrain-selected-cannot-claim">${esc(packet.cannot_claim.slice(0, 4).join(" | "))}</p>
        </section>
        <section class="inspector-section" data-inspector-section="review-state">
          <h4>Review state</h4>
          <p id="citybrain-selected-review-state">${esc(review.review_state_ref || "review_state:mobility_access:not_executed")} | approved_proposal_created=${esc(review.approved_proposal_created ?? false)}</p>
          <p>Local operator state: <strong id="citybrain-local-review-state">hold</strong></p>
        </section>
        <section class="inspector-section" data-inspector-section="no-action">
          <h4>No action</h4>
          <p id="citybrain-selected-no-action">NoActionState: no_action_taken=true | execution_state=not_executed | actions=not_executed</p>
        </section>
        <section class="inspector-section" data-inspector-section="source-refs-packet-hash">
          <h4>Source refs / packet hash</h4>
          <p>Source refs: ${sourceRefText}</p>
          <p id="citybrain-selected-packet-hash">Packet hash: pending</p>
        </section>
        <section class="inspector-section workflow-section" data-inspector-section="workflow-state">
          <h4>Local workflow</h4>
          <div class="state-button-row" aria-label="Local review workflow states">
            ${CITYBRAIN_R6_WORKFLOW_STATES.map((state) => `<button type="button" data-workflow-state-action="${esc(state)}">${esc(buttonTextState(state))}</button>`).join("")}
          </div>
          <label class="local-note-label" for="citybrain-review-note">Review note</label>
          <textarea id="citybrain-review-note" rows="4" placeholder="Add a local review note. This creates no case, dispatch, or action."></textarea>
          <div class="state-button-row">
            <button type="button" data-review-note-save="true">Add note</button>
            <button type="button" data-review-export-json="true">Export JSON</button>
            <button type="button" data-review-export-md="true">Export Markdown</button>
          </div>
          <p id="citybrain-review-export-status">No local export yet. Export remains review-only and not_executed.</p>
        </section>
      </aside>
    </div>
    <div class="record-grid two-col stream-boundary-grid">
      <article class="mini-record">
        <strong>Knowns / summary</strong>
        <span>${esc(scenario.hero_spine || bundle?.oneTruth?.hero_spine || "Mobility Access corridor review context")}</span>
        <span>Overlay packet source: kit_overlay_packets.json</span>
      </article>
      <article class="mini-record">
        <strong>R5 parity preserved</strong>
        <span>Object and event focus messages remain packet-driven. Current event default: ${esc(firstEvent.event_id)}.</span>
        <span id="omniverse-webrtc-message-state">Allowed messages are selection/event focus/changed and stream state only; action-like messages are rejected with execution_state=not_executed.</span>
      </article>
    </div>
  </section>`;
}

function appStreamerConstructor() {
  if (typeof window === "undefined") return null;
  return window.OVWebRTC?.AppStreamer
    || window.OV?.AppStreamer
    || window.OmniverseWebSdk?.AppStreamer
    || window.AppStreamer
    || null;
}

function readConfig(root) {
  if (typeof window === "undefined") return { ...DEFAULT_WEBRTC_CONFIG };
  try {
    const override = JSON.parse(window.localStorage.getItem("citybrain.omniverse.webrtc.config") || "{}");
    return { ...DEFAULT_WEBRTC_CONFIG, ...override };
  } catch {
    return { ...DEFAULT_WEBRTC_CONFIG, packet_truth_root: root?.dataset.packetTruthRoot || DEFAULT_WEBRTC_CONFIG.packet_truth_root };
  }
}

function packetFromRoot(root) {
  const evidenceRefs = readJson(root?.dataset.evidenceRefs, []);
  const limitationRefs = readJson(root?.dataset.limitationRefs, []);
  const reviewState = readJson(root?.dataset.reviewState, {});
  const noActionState = readJson(root?.dataset.noActionState, {});
  const cannotClaim = readJson(root?.dataset.cannotClaim, [...NO_ACTION_CANNOT_CLAIM]);
  return {
    schema_version: "citybrain.omniverse.selection_packet.canonical.r1",
    canonical_entity_id: root?.dataset.selectedEntityRef || "",
    entity_type: root?.dataset.selectedEntityType || entityTypeFromRef(root?.dataset.selectedEntityRef),
    entity_label: entityLabelFromRef(root?.dataset.selectedEntityRef),
    prim_path: root?.dataset.selectedPrimPath || "",
    selected_event_id: root?.dataset.selectedEventId || "",
    selected_event_marker_path: root?.dataset.selectedEventMarkerPath || "",
    evidence_refs: evidenceRefs,
    limitation_refs: limitationRefs,
    review_state: reviewState,
    no_action_state: noActionState,
    cannot_claim: cannotClaim
  };
}

function setText(root, selector, value) {
  const node = root?.querySelector(selector);
  if (node) node.textContent = String(value ?? "");
}

function readStorageArray(key) {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

function writeStorageArray(key, rows) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(rows.slice(-100)));
}

function recordSelectionMessage(message) {
  if (typeof window === "undefined") return;
  window.__CITYBRAIN_SELECTION_MESSAGES__ = window.__CITYBRAIN_SELECTION_MESSAGES__ || [];
  window.__CITYBRAIN_SELECTION_MESSAGES__.push(message);
}

function recordWorkflowTransition(entry) {
  if (typeof window === "undefined") return;
  const rows = readStorageArray(WORKFLOW_TRANSITION_KEY);
  rows.push(entry);
  writeStorageArray(WORKFLOW_TRANSITION_KEY, rows);
  window.__CITYBRAIN_R6_WORKFLOW_TRANSITIONS__ = rows;
}

function selectedDisplayLabel(root, packet) {
  if (root?.dataset.selectedKind === "event" && root.dataset.selectedEventId) return root.dataset.selectedEventId;
  return packet.entity_label || packet.canonical_entity_id || "CityBrain selection";
}

function applySelectionMessageToDom(message, root) {
  const packet = message.packet || {
    canonical_entity_id: message.canonical_entity_id || message.entity_ref,
    entity_type: message.entity_type || entityTypeFromRef(message.canonical_entity_id || message.entity_ref),
    entity_label: message.entity_label || entityLabelFromRef(message.canonical_entity_id || message.entity_ref),
    prim_path: message.prim_path,
    evidence_refs: message.evidence_refs || [],
    limitation_refs: message.limitation_refs || [],
    review_state: message.review_state || {},
    no_action_state: message.no_action_state || { no_action_taken: true, execution_state: "not_executed" },
    cannot_claim: message.cannot_claim || [...NO_ACTION_CANNOT_CLAIM]
  };
  const target = root || (typeof document !== "undefined" ? document.querySelector("#omniverse-webrtc-bridge") : null);
  if (!target) return { status: "NO_PANEL" };

  target.dataset.selectedKind = message.event_id ? "event" : "object";
  target.dataset.selectedEntityRef = packet.canonical_entity_id || "";
  target.dataset.selectedEntityType = packet.entity_type || entityTypeFromRef(packet.canonical_entity_id);
  target.dataset.selectedPrimPath = packet.prim_path || message.target_prim_path || "";
  target.dataset.selectedEventId = message.event_id || packet.selected_event_id || "";
  target.dataset.selectedEventMarkerPath = message.marker_prim_path || packet.selected_event_marker_path || "";
  target.dataset.evidenceRefs = JSON.stringify(packet.evidence_refs || []);
  target.dataset.limitationRefs = JSON.stringify(packet.limitation_refs || []);
  target.dataset.reviewState = JSON.stringify(packet.review_state || {});
  target.dataset.noActionState = JSON.stringify(packet.no_action_state || {});
  target.dataset.cannotClaim = JSON.stringify(packet.cannot_claim || []);
  target.dataset.packetHash = message.packet_hash || packet.packet_hash || target.dataset.packetHash || "";
  target.dataset.selectionSource = message.selection_source || target.dataset.selectionSource || "kit_native_cockpit";
  target.dataset.executionState = packet.no_action_state?.execution_state || "not_executed";

  const canonical = message.event_id || packet.canonical_entity_id || "";
  const primOrMarker = message.marker_prim_path || packet.prim_path || message.target_prim_path || "";
  setText(target, "#citybrain-selected-entity-title", selectedDisplayLabel(target, packet));
  setText(target, "#citybrain-selected-entity-ref", canonical);
  setText(target, "#citybrain-selected-canonical-id", canonical);
  setText(target, "#citybrain-selected-prim-path", primOrMarker);
  setText(target, "#citybrain-selected-evidence", `refs=${(packet.evidence_refs || []).length} | ${(packet.evidence_refs || []).slice(0, 4).join(", ")}`);
  setText(target, "#citybrain-selected-limitations", (packet.limitation_refs || []).slice(0, 4).join(" | "));
  setText(
    target,
    "#citybrain-selected-review-state",
    `${packet.review_state?.review_state_ref || "review_state:mobility-access:not_executed"} | approved_proposal_created=${String(packet.review_state?.approved_proposal_created ?? false)}`
  );
  setText(
    target,
    "#citybrain-selected-no-action",
    `NoActionState: no_action_taken=${String(packet.no_action_state?.no_action_taken ?? true)} | execution_state=${packet.no_action_state?.execution_state || "not_executed"} | actions=not_executed`
  );
  setText(target, "#citybrain-selected-cannot-claim", (packet.cannot_claim || []).slice(0, 4).join(" | "));
  setText(target, "#citybrain-selected-packet-hash", `Packet hash: ${message.packet_hash || packet.packet_hash || target.dataset.packetHash || "pending"}`);
  return {
    status: "APPLIED_PACKET_SELECTION_TO_WEB_DOM",
    canonical_entity_id: packet.canonical_entity_id,
    event_id: message.event_id || "",
    packet_hash: message.packet_hash || target.dataset.packetHash || "",
    pixel_derived_truth_used: false
  };
}

export async function buildCityBrainSelectionMessage(root, direction = "web_to_kit", selectionSource = "web_ui") {
  const target = root || (typeof document !== "undefined" ? document.querySelector("#omniverse-webrtc-bridge") : null);
  const packet = packetFromRoot(target);
  const packetHash = await sha256Hex(packet);
  if (target) target.dataset.packetHash = packetHash;
  const isEvent = target?.dataset.selectedKind === "event" && target.dataset.selectedEventId;
  const messageType = isEvent
    ? (direction === "kit_to_web" ? "citybrain.event.selection_changed" : "citybrain.event.focus_request")
    : (direction === "kit_to_web" ? "citybrain.selection.changed" : "citybrain.selection.focus_request");
  return {
    schema_version: "citybrain.omniverse.webrtc.selection_message_parity.r6",
    type: messageType,
    message_type: messageType,
    message_id: `${direction}:${isEvent ? target.dataset.selectedEventId : packet.canonical_entity_id}:${packetHash.slice(0, 12)}`,
    direction,
    canonical_entity_id: packet.canonical_entity_id,
    entity_type: packet.entity_type,
    entity_label: packet.entity_label,
    prim_path: packet.prim_path,
    event_id: target?.dataset.selectedEventId || "",
    marker_prim_path: target?.dataset.selectedEventMarkerPath || "",
    selection_source: selectionSource,
    evidence_refs: packet.evidence_refs,
    limitation_refs: packet.limitation_refs,
    review_state: packet.review_state,
    no_action_state: packet.no_action_state,
    cannot_claim: packet.cannot_claim,
    timestamp: new Date().toISOString(),
    packet_hash: packetHash,
    packet,
    pixel_derived_truth_used: false,
    stream_visual_context_only: true,
    review_only: true,
    execution_state: "not_executed",
    no_action_taken: true
  };
}

export async function buildLocalReviewPacket(root, noteText = "") {
  const target = root || (typeof document !== "undefined" ? document.querySelector("#omniverse-webrtc-bridge") : null);
  const packet = packetFromRoot(target);
  const localReviewState = target?.dataset.localReviewState || "hold";
  const packetHash = target?.dataset.packetHash || await sha256Hex(packet);
  const exportPacket = {
    schema_version: "citybrain.omniverse.webrtc.r6.local_review_export.v1",
    selected_kind: target?.dataset.selectedKind || "object",
    selected_object_or_event_packet: packet,
    selected_event_id: target?.dataset.selectedEventId || "",
    selected_event_marker_path: target?.dataset.selectedEventMarkerPath || "",
    local_review_state: localReviewState,
    note_text: noteText,
    evidence_refs: packet.evidence_refs,
    limitation_refs: packet.limitation_refs,
    does_not_prove: packet.cannot_claim,
    cannot_claim: packet.cannot_claim,
    no_action_state: packet.no_action_state,
    packet_hash: packetHash,
    local_timestamp: new Date().toISOString(),
    review_state_local_only: true,
    pixel_derived_truth_used: false,
    stream_visual_context_only: true,
    actions: "not_executed"
  };
  exportPacket.export_hash = await sha256Hex(exportPacket);
  return exportPacket;
}

function exportMarkdown(packet) {
  return [
    "# CityBrain local review export",
    "",
    `Selected kind: ${packet.selected_kind}`,
    `Local review state: ${packet.local_review_state}`,
    `Packet hash: ${packet.packet_hash}`,
    `Export hash: ${packet.export_hash}`,
    "",
    "## Note",
    packet.note_text || "No note entered.",
    "",
    "## Evidence",
    ...packet.evidence_refs.map((ref) => `- ${ref}`),
    "",
    "## Limitations",
    ...packet.limitation_refs.map((ref) => `- ${ref}`),
    "",
    "## Does Not Prove",
    ...packet.cannot_claim.map((ref) => `- ${ref}`),
    "",
    "## No Action",
    `no_action_taken=${packet.no_action_state?.no_action_taken !== false}`,
    `execution_state=${packet.no_action_state?.execution_state || "not_executed"}`
  ].join("\n");
}

function downloadReviewExport(packet, format) {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const content = format === "md" ? exportMarkdown(packet) : JSON.stringify(packet, null, 2);
  const extension = format === "md" ? "md" : "json";
  const mime = format === "md" ? "text/markdown" : "application/json";
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `citybrain_r6_local_review_${packet.export_hash.slice(0, 12)}.${extension}`;
  link.click();
  URL.revokeObjectURL(url);
}

export function applyKitToWebSelectionMessage(message, root = null) {
  const messageType = String(message?.type || message?.message_type || "");
  if (!["citybrain.selection.changed", "citybrain.event.selection_changed", "citybrain.event.overlay_upsert"].includes(messageType)) {
    return {
      status: "IGNORED_NON_SELECTION_CHANGED_MESSAGE",
      message_type: messageType,
      pixel_derived_truth_used: false
    };
  }
  const verdict = classifyWebRtcMessage(message);
  if (verdict.status !== "ACCEPTED_REVIEW_ONLY") {
    return { ...verdict, pixel_derived_truth_used: false };
  }
  const applied = applySelectionMessageToDom(message, root);
  recordSelectionMessage(message);
  return { ...applied, message_type: messageType, verdict };
}

function setSideRailState(root, expanded) {
  const rail = root.querySelector("#citybrain-operator-side-rail");
  const nextState = expanded ? "expanded" : "collapsed";
  root.dataset.inspectorCollapsibleState = nextState;
  rail?.setAttribute("data-side-rail-state", nextState);
  root.querySelectorAll("[data-side-rail-toggle]").forEach((button) => {
    button.setAttribute("aria-expanded", String(expanded));
    button.textContent = expanded ? "Collapse inspector" : "Expand inspector";
  });
  if (typeof window !== "undefined") {
    window.localStorage.setItem("citybrain.omniverse.r6.sideRailState", nextState);
  }
}

function applyWorkflowState(root, state, source = "button") {
  const normalized = state === "clear/reset" || state === "cleared_reset" ? "cleared/reset" : state;
  root.dataset.localReviewState = normalized;
  setText(root, "#citybrain-local-review-state", normalized);
  const entry = {
    schema_version: "citybrain.omniverse.webrtc.r6.workflow_transition.v1",
    state: normalized,
    source,
    selected_kind: root.dataset.selectedKind || "object",
    selected_entity_ref: root.dataset.selectedEntityRef || "",
    selected_event_id: root.dataset.selectedEventId || "",
    timestamp: new Date().toISOString(),
    review_state_local_only: true,
    no_action_state: "not_executed"
  };
  if (normalized === "cleared/reset") {
    root.querySelector("#citybrain-review-note").value = "";
  }
  recordWorkflowTransition(entry);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify({ state: normalized, updated_at: entry.timestamp }));
  }
  return entry;
}

export function initializeOmniverseStreamPanel() {
  if (typeof document === "undefined") return { status: "NO_DOCUMENT" };
  const root = document.querySelector("#omniverse-webrtc-bridge");
  if (!root) return { status: "NO_PANEL" };
  const stateLabel = root.querySelector("#omniverse-webrtc-session-state");
  const detail = root.querySelector("#omniverse-webrtc-stream-detail");
  const messageState = root.querySelector("#omniverse-webrtc-message-state");
  const container = root.querySelector("#omniverse-webrtc-stream-container");
  const config = readConfig(root);
  let streamer = null;

  const setStatus = (status, copy) => {
    root.dataset.streamStatus = status;
    if (stateLabel) stateLabel.textContent = `WebRTC: ${copy || status.replace(/_/g, " ")}`;
    if (detail) detail.textContent = copy || status.replace(/_/g, " ");
  };

  const sendMessage = (message) => {
    const verdict = classifyWebRtcMessage(message);
    if (messageState) messageState.textContent = `${verdict.type}: ${verdict.status}; execution_state=${verdict.execution_state}`;
    if (verdict.status !== "ACCEPTED_REVIEW_ONLY") return verdict;
    recordSelectionMessage(message);
    const appMessage = { event_type: message.message_type || message.type, payload: message };
    if (streamer?.sendMessage) streamer.sendMessage(appMessage);
    if (streamer?.sendCustomMessage) streamer.sendCustomMessage(appMessage);
    const primToSelect = message.marker_prim_path || message.prim_path;
    if (primToSelect && streamer?.setSelectedPrims) streamer.setSelectedPrims([primToSelect]);
    return verdict;
  };

  const connect = async () => {
    const AppStreamer = appStreamerConstructor();
    if (!AppStreamer) {
      setStatus("blocked_missing_ov_web_sdk", "blocked: Omniverse Web SDK AppStreamer is not loaded");
      return { status: "BLOCKED_MISSING_OV_WEB_SDK" };
    }
    setStatus("connecting", "connecting to local Kit livestream");
    try {
      if (typeof AppStreamer.connect === "function" && typeof AppStreamer.sendMessage === "function") {
        await AppStreamer.connect({
          streamSource: "direct",
          logLevel: "info",
          streamConfig: {
            videoElementId: "omniverse-webrtc-remote-video",
            signalingServer: "127.0.0.1",
            signalingPort: config.signal_port,
            width: 1920,
            height: 1080,
            fps: 60,
            onStart: () => setStatus("connected", "connected to local Kit WebRTC stream"),
            onCustomEvent: (message) => applyKitToWebSelectionMessage(message?.payload || message, root),
            onStop: () => setStatus("stopped", "local Kit WebRTC stream stopped")
          }
        });
        streamer = AppStreamer;
      } else {
        streamer = new AppStreamer({
          container,
          targetElement: container,
          sessionServiceUrl: config.session_service_url,
          signalingUrl: config.signaling_url,
          streamPort: config.stream_port,
          signalPort: config.signal_port,
          fullKitUi: true,
          localOnly: true
        });
        if (typeof streamer.connect === "function") {
          await streamer.connect();
        } else if (typeof streamer.start === "function") {
          await streamer.start();
        }
      }
      setStatus("connected", "connected to local Kit WebRTC stream");
      return { status: "CONNECTED" };
    } catch (error) {
      setStatus("blocked_connection_failed", `blocked: ${error.message || "local Kit WebRTC connection failed"}`);
      return { status: "BLOCKED_CONNECTION_FAILED", error: String(error.message || error) };
    }
  };

  const storedRailState = window.localStorage.getItem("citybrain.omniverse.r6.sideRailState") || "expanded";
  setSideRailState(root, storedRailState !== "collapsed");

  root.querySelectorAll("[data-side-rail-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      setSideRailState(root, root.dataset.inspectorCollapsibleState === "collapsed");
    });
  });

  root.querySelectorAll("[data-workflow-state-action]").forEach((button) => {
    button.addEventListener("click", () => applyWorkflowState(root, button.dataset.workflowStateAction || "hold"));
  });

  root.querySelector("[data-review-note-save]")?.addEventListener("click", () => {
    const noteInput = root.querySelector("#citybrain-review-note");
    applyWorkflowState(root, "note_added", "note_button");
    const entry = {
      schema_version: "citybrain.omniverse.webrtc.r6.note_event.v1",
      note_text: noteInput?.value || "",
      selected_entity_ref: root.dataset.selectedEntityRef || "",
      selected_event_id: root.dataset.selectedEventId || "",
      timestamp: new Date().toISOString(),
      review_state_local_only: true,
      no_action_state: "not_executed"
    };
    const rows = readStorageArray("citybrain.omniverse.r6.operatorWorkflow.notes");
    rows.push(entry);
    writeStorageArray("citybrain.omniverse.r6.operatorWorkflow.notes", rows);
    setText(root, "#citybrain-review-export-status", "Local note saved. No official case, dispatch, or action was created.");
  });

  root.querySelector("[data-review-export-json]")?.addEventListener("click", async () => {
    const noteText = root.querySelector("#citybrain-review-note")?.value || "";
    const packet = await buildLocalReviewPacket(root, noteText);
    const rows = readStorageArray(WORKFLOW_EXPORT_KEY);
    rows.push(packet);
    writeStorageArray(WORKFLOW_EXPORT_KEY, rows);
    window.__CITYBRAIN_R6_EXPORTS__ = rows;
    setText(root, "#citybrain-review-export-status", `JSON export ready: ${packet.export_hash}. Review only; execution_state=not_executed.`);
    downloadReviewExport(packet, "json");
  });

  root.querySelector("[data-review-export-md]")?.addEventListener("click", async () => {
    const noteText = root.querySelector("#citybrain-review-note")?.value || "";
    const packet = await buildLocalReviewPacket(root, noteText);
    setText(root, "#citybrain-review-export-status", `Markdown export ready: ${packet.export_hash}. Review only; execution_state=not_executed.`);
    downloadReviewExport(packet, "md");
  });

  root.querySelectorAll("[data-webrtc-command]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.webrtcCommand === "connect") connect();
      if (button.dataset.webrtcCommand === "bookmark") {
        const bookmark = button.dataset.sceneBookmark || "overview";
        const targetPrim = bookmark === "event" ? root.dataset.selectedEventMarkerPath : root.dataset.selectedPrimPath;
        const message = {
          schema_version: "citybrain.omniverse.webrtc.viewport_navigation.r6",
          type: "citybrain.viewport.navigate",
          message_type: "citybrain.viewport.navigate",
          action: `bookmark_${bookmark}`,
          target_prim_path: targetPrim,
          review_only: true,
          execution_state: "not_executed",
          pixel_derived_truth_used: false,
          stream_visual_context_only: true,
          timestamp: new Date().toISOString()
        };
        recordSelectionMessage(message);
        if (messageState) messageState.textContent = `viewport ${bookmark}: review-only frame request; execution_state=not_executed`;
      }
    });
  });

  root.querySelectorAll("[data-webrtc-select-entity]").forEach((button) => {
    button.addEventListener("click", () => {
      root.dataset.selectedKind = "object";
      root.dataset.selectedEventId = "";
      root.dataset.selectedEventMarkerPath = "";
      root.dataset.selectedEntityRef = button.dataset.entityRef || "";
      root.dataset.selectedEntityType = button.dataset.entityType || entityTypeFromRef(button.dataset.entityRef);
      root.dataset.selectedPrimPath = button.dataset.primPath || "";
      const evidenceRefs = readJson(root.dataset.evidenceRefs, []);
      root.dataset.evidenceRefs = JSON.stringify([
        button.dataset.entityRef,
        ...evidenceRefs.filter((ref) => !String(ref).startsWith("mobility_access:"))
      ]);
      buildCityBrainSelectionMessage(root, "web_to_kit", "web_ui_entity_button").then((message) => {
        applySelectionMessageToDom(message, root);
        sendMessage(message);
      });
    });
  });

  root.querySelectorAll("[data-webrtc-select-event]").forEach((button) => {
    button.addEventListener("click", () => {
      const eventPacket = readJson(button.dataset.eventPacket, eventPacketFromEvent(EVENT_REVIEW_PACKETS[0]));
      root.dataset.selectedKind = "event";
      root.dataset.selectedEventId = eventPacket.event_id || button.dataset.eventId || "";
      root.dataset.selectedEventMarkerPath = eventPacket.marker_prim_path || button.dataset.markerPrimPath || "";
      root.dataset.selectedEntityRef = eventPacket.canonical_entity_id || "";
      root.dataset.selectedEntityType = "event_overlay";
      root.dataset.selectedPrimPath = eventPacket.target_prim_path || button.dataset.targetPrimPath || "";
      root.dataset.evidenceRefs = JSON.stringify(eventPacket.evidence_refs || []);
      root.dataset.limitationRefs = JSON.stringify(eventPacket.limitation_refs || []);
      root.dataset.reviewState = JSON.stringify(eventPacket.review_state || {});
      root.dataset.noActionState = JSON.stringify(eventPacket.no_action_state || {});
      root.dataset.cannotClaim = JSON.stringify(eventPacket.cannot_claim || []);
      const message = {
        ...eventPacket,
        type: "citybrain.event.focus_request",
        message_type: "citybrain.event.focus_request",
        direction: "web_to_kit",
        selection_source: "web_ui_event_button",
        timestamp: new Date().toISOString()
      };
      applySelectionMessageToDom(message, root);
      sendMessage(message);
    });
  });

  window.addEventListener("message", (event) => {
    const payload = event.data && typeof event.data === "object" ? event.data : {};
    if (!String(payload.type || payload.message_type || "").startsWith("citybrain.")) return;
    const verdict = classifyWebRtcMessage(payload);
    if (["citybrain.selection.changed", "citybrain.event.selection_changed", "citybrain.event.overlay_upsert"].includes(String(payload.type || payload.message_type || ""))) {
      applyKitToWebSelectionMessage(payload, root);
    }
    if (messageState) messageState.textContent = `${verdict.type}: ${verdict.status}; execution_state=${verdict.execution_state}`;
  });

  setStatus("ready_local_dev", "ready for local Kit WebRTC session");
  applyWorkflowState(root, root.dataset.localReviewState || "hold", "initial_state");
  return { status: "READY_LOCAL_DEV", config };
}
