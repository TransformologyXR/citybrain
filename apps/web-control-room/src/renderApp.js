import { hasStoryQueueBundle, renderStoryQueue } from "./views/storyQueue.js";
import { hasStoryFirstBundle, renderStoryFirst } from "./views/storyFirst.js";
import { hasProductModesBundle, renderProductModes } from "./views/productModes.js";
import { initializeOmniverseStreamPanel, renderOmniverseStreamPanel } from "./views/omniverseStream.js";
import { hasAskV11HandoffBundle, initializeAskV11HandoffMode, renderAskV11Handoff } from "./views/askV11Handoff.js";

const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

const SOURCE_RECORD_CLASSES = new Set(["OFFICIAL_CITY_SOURCE_RECORD", "SOURCE_DERIVED_CITY_RECORD"]);

const emptyIntegratedBundle = {
  status: "SOURCE_RECORD_UI_INTEGRATED_BUNDLE_MISSING",
  situation_city_records: [],
  similar_case_city_records: [],
  visual_entity_city_records: [],
  media_observation_source_records: [],
  guardrail_refusal_review_records: [],
  human_review_stop_source_records: [],
  scenario_coherence_verdict: {
    status: "UNKNOWN",
    viewer_framing: "source-record review surface"
  },
  data_depth_blockers: [
    {
      card_id: "integrated-source-record-ui-bundle-missing",
      record_class: "DATA_DEPTH_BLOCKER",
      title: "DATA DEPTH BLOCKER: integrated city-record bundle missing",
      plain_language_summary: "The web control room could not load the integrated source-record UI bundle. It will not present fixture labels as city facts.",
      missing_record: "source-record UI integrated bundle",
      required_next_data: "Run the D8 source-record UI integration adapter."
    }
  ],
  technical_refs: {}
};

function integratedPayload(bundle) {
  const integrated = bundle.integratedSourceRecords?.bundle;
  if (integrated?.situation_city_records || integrated?.similar_case_city_records || integrated?.visual_entity_city_records) {
    return integrated;
  }
  return emptyIntegratedBundle;
}

function allCityRecords(payload) {
  return [
    ...(payload.situation_city_records || []),
    ...(payload.similar_case_city_records || []),
    ...(payload.visual_entity_city_records || []),
    ...(payload.media_observation_source_records || []),
    ...(payload.guardrail_refusal_review_records || []),
    ...(payload.human_review_stop_source_records || [])
  ];
}

function sourceBackedRecords(payload) {
  return allCityRecords(payload).filter((record) => SOURCE_RECORD_CLASSES.has(record.record_class || record.card_classification));
}

function blockers(payload) {
  return payload.data_depth_blockers || [];
}

function listItems(items, fallback = "None recorded.") {
  if (!items?.length) return `<li>${esc(fallback)}</li>`;
  return items.map((item) => `<li>${esc(item)}</li>`).join("");
}

function chipItems(items, fallback = "None recorded") {
  if (!items?.length) return `<span class="chip muted">${esc(fallback)}</span>`;
  return items.map((item) => `<span class="chip">${esc(item)}</span>`).join("");
}

function fieldRows(fields = {}) {
  const entries = Object.entries(fields).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) return `<p class="muted-copy">No plain-language source fields were provided for this record.</p>`;
  return `<div class="record-meta">${entries.map(([key, value]) => `<span>${esc(key.replace(/_/g, " "))}: ${esc(value)}</span>`).join("")}</div>`;
}

function actionText(value) {
  const text = String(value || "").replace(/^review_/, "").replace(/_option$/, "").replace(/_/g, " ");
  if (!text || text === "do nothing monitor") return "Keep the baseline and continue human review.";
  if (text === "kerbside access") return "Review kerbside access support.";
  if (text === "public information draft") return "Review a public-information draft.";
  if (text === "reroute") return "Review a reroute idea.";
  if (text === "escalate to human operator") return "Abstain and ask a human operator for direction.";
  return `Review ${text}.`;
}

function recordClassLabel(record) {
  const cls = record.record_class || record.card_classification;
  if (cls === "OFFICIAL_CITY_SOURCE_RECORD") return "Official city source record";
  if (cls === "SOURCE_DERIVED_CITY_RECORD") return "Source-derived city record";
  if (cls === "LOCAL_DEMO_MEDIA_OBSERVATION_RECORD") return "Local demo-media observation record";
  if (cls === "GOVERNANCE_REVIEW_LOG_RECORD") return "Governance review-log record";
  if (cls === "HUMAN_REVIEW_STOP_RECORD") return "Human review-stop record";
  if (cls === "DATA_DEPTH_BLOCKER") return "Data depth blocker";
  return "Record";
}

function renderHero(bundle) {
  const payload = integratedPayload(bundle);
  const londonCount = payload.situation_city_records?.length || 0;
  const chicagoCount = payload.similar_case_city_records?.length || 0;
  const helsinkiCount = payload.visual_entity_city_records?.length || 0;
  const observationCount = payload.media_observation_source_records?.length || 0;
  const refusalCount = payload.guardrail_refusal_review_records?.length || 0;
  const reviewStopCount = payload.human_review_stop_source_records?.length || 0;
  const blockerCount = blockers(payload).length;
  const sourceCount = sourceBackedRecords(payload).length;
  const scenarioStatus = payload.scenario_coherence_verdict?.status || "UNKNOWN";
  const ready = sourceCount >= 20 && observationCount > 0 && refusalCount > 0 && reviewStopCount > 0;
  return `<section id="city-fact-verdict" class="hero-panel span-12" data-panel="city-fact-verdict">
    <div class="hero-copy">
      <p class="eyebrow">Source-record review surface</p>
      <h2>${ready ? "Source records and review stops are visible by default" : "Source records still need more depth"}</h2>
      <p class="hero-line">${ready
        ? "Source-record portfolio: the page opens on London mobility examples, Chicago precedent context, Helsinki visual-entity picks, local demo-media observation records, refusal logs, and human-review stops."
        : "The page will show only recovered records and explicit data-depth blockers; it will not turn fixture labels into city facts."}</p>
      <div class="plain-status-row">
        <span class="status-pill safe">London records: ${londonCount}</span>
        <span class="status-pill safe">Chicago records: ${chicagoCount}</span>
        <span class="status-pill safe">Helsinki records: ${helsinkiCount}</span>
        <span class="status-pill safe">Observation records: ${observationCount}</span>
        <span class="status-pill safe">Refusal records: ${refusalCount}</span>
        <span class="status-pill safe">Review stops: ${reviewStopCount}</span>
        <span class="status-pill">Open blockers: ${blockerCount}</span>
        <span class="status-pill">Scenario coherence: ${esc(scenarioStatus)}</span>
        <span class="status-pill safe">No action has been taken</span>
      </div>
    </div>
    <div class="hero-note">
      <strong>Viewer-capture decision</strong>
      <p>${blockerCount
        ? "Use this for internal source-backed capture. Keep full naive viewer validation gated until the blocker cards are resolved or deliberately accepted."
        : "Ready for internal source-record capture. External naive-viewer validation still depends on accepting that this is a portfolio, not one proven corridor incident."}</p>
    </div>
  </section>`;
}

function renderTruthRegister(bundle) {
  const payload = integratedPayload(bundle);
  const checks = [
    ["Default city-record cards", `${sourceBackedRecords(payload).length} recovered records`],
    ["London mobility records", `${payload.situation_city_records?.length || 0}`],
    ["Chicago precedent records", `${payload.similar_case_city_records?.length || 0}`],
    ["Helsinki visual picks", `${payload.visual_entity_city_records?.length || 0}`],
    ["Observation records", `${payload.media_observation_source_records?.length || 0}`],
    ["Refusal records", `${payload.guardrail_refusal_review_records?.length || 0}`],
    ["Human review stops", `${payload.human_review_stop_source_records?.length || 0}`],
    ["Source-depth blockers", `${blockers(payload).length}`],
    ["Story framing", payload.scenario_coherence_verdict?.viewer_framing || "source-record portfolio"],
    ["Review boundary", "Human review only; no approval or execution"]
  ];
  return `<section id="current-ui-truth" class="panel span-12" data-panel="current-ui-truth">
    <p class="section-kicker">Current screen truth</p>
    <h2>What the default view can honestly show</h2>
    <div class="metric-grid">
      ${checks.map(([label, value]) => `<div class="metric"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}
    </div>
    <p class="human-explain">Every default card below is either backed by a recovered source/review record or is an explicit data-depth blocker. The London records are supporting examples, not proof of one lane-blockage incident.</p>
  </section>`;
}

function renderCoherenceVerdict(bundle) {
  const payload = integratedPayload(bundle);
  const verdict = payload.scenario_coherence_verdict || {};
  return `<section id="scenario-coherence-verdict" class="panel span-12" data-panel="scenario-coherence-verdict">
    <p class="section-kicker">Scenario coherence</p>
    <h2>${esc(verdict.default_ui_headline || "Source records are valid; scenario linkage remains bounded")}</h2>
    <p class="human-explain">${esc(verdict.viewer_summary || "The default view should frame these records as a source-record portfolio unless a source record proves one shared corridor incident.")}</p>
    <div class="metric-grid two">
      <div class="metric"><span>London source linkage</span><strong>${esc(verdict.london_linkage_status || "not proven as one corridor incident")}</strong></div>
      <div class="metric"><span>Allowed viewer framing</span><strong>${esc(verdict.viewer_framing || "source-record portfolio")}</strong></div>
    </div>
  </section>`;
}

function renderCityRecord(record) {
  return `<article id="${esc(record.card_id)}" class="fact-card" data-card-classification="${esc(record.record_class || record.card_classification)}" data-card-type="${esc(record.card_type)}">
    <span class="record-type">${esc(recordClassLabel(record))}</span>
    <h3>${esc(record.title)}</h3>
    <p>${esc(record.plain_language_summary || record.summary)}</p>
    ${fieldRows(record.city_fact_fields || record.evidence_fields)}
    <div class="record-grid two-col">
      <div>
        <h3>Why it matters here</h3>
        <p>${esc(record.why_it_matters || record.match_reason || "This record adds source-backed context. It is not an instruction or a finding.")}</p>
      </div>
      <div>
        <h3>Limits on the record</h3>
        <ul class="plain-list compact">${listItems((record.limitations || []).slice(0, 3))}</ul>
      </div>
    </div>
    <div class="chip-row">${chipItems(record.evidence_refs || [record.source_url].filter(Boolean), "Source reference retained in technical details")}</div>
  </article>`;
}

function renderRecordSection(id, kicker, title, copy, records) {
  return `<section id="${esc(id)}" class="panel span-12" data-panel="${esc(id)}">
    <p class="section-kicker">${esc(kicker)}</p>
    <h2>${esc(title)}</h2>
    <p class="human-explain">${esc(copy)}</p>
    <div class="record-grid two-col">
      ${(records || []).map(renderCityRecord).join("") || `<article class="fact-card gap-card"><span class="record-type">Data depth blocker</span><h3>No renderable records</h3><p>This panel has no source-backed cards in the integrated bundle.</p></article>`}
    </div>
  </section>`;
}

function renderOptionReview(bundle) {
  const options = bundle.options?.candidate_options || [];
  const visible = options.slice(0, 7);
  return `<section id="review-choice-comparison" class="panel span-12" data-panel="review-choice-comparison">
    <p class="section-kicker">Review-only choices</p>
    <h2>Options remain candidates for a human</h2>
    <p class="human-explain">These choices are displayed as review context only. They do not approve, dispatch, route, control, enforce, or execute anything.</p>
    <div class="record-grid three-col">
      ${visible.map((option, index) => `<article class="fact-card">
        <span class="record-type">${index === 0 ? "Baseline" : option.option_role === "abstain_or_escalate" ? "Abstain path" : "Candidate choice"}</span>
        <h3>${esc(actionText(option.option_type))}</h3>
        <p>${esc(option.required_human_decision === "review_context_only" ? "Keep this as context for a human reviewer." : "A human would have to decide whether this becomes a proposal.")}</p>
        <div class="record-meta">
          <span>Access continuity: review axis</span>
          <span>Delay risk: review axis</span>
          <span>Kerbside safety: review axis</span>
          <span>Evidence confidence: review axis</span>
        </div>
        <p class="muted-copy">Action state: no approval and no execution.</p>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderBlockers(bundle) {
  const payload = integratedPayload(bundle);
  const gapCards = blockers(payload);
  if (!gapCards.length) {
    return `<section id="source-depth-blockers" class="panel span-12" data-panel="source-depth-blockers">
      <p class="section-kicker">Data-depth gaps</p>
      <h2>Former blockers now have viewer records</h2>
      <p class="human-explain">The candidate-observation, refusal-log, and human-review-stop moments now render as bounded source/review records. Remaining limitations are shown in the ledger instead of hidden behind a clean bill of health.</p>
    </section>`;
  }
  return `<section id="source-depth-blockers" class="panel span-12" data-panel="source-depth-blockers">
    <p class="section-kicker">Data-depth gaps</p>
    <h2>What still cannot be shown as a city fact</h2>
    <div class="record-grid three-col">
      ${gapCards.map((gap) => `<article class="fact-card gap-card" data-card-classification="DATA_DEPTH_BLOCKER">
        <span class="record-type">Data depth blocker</span>
        <h3>${esc(gap.title)}</h3>
        <p>${esc(gap.plain_language_summary || gap.summary)}</p>
        <div class="record-meta">
          <span>Missing record: ${esc(gap.missing_record || "not recorded")}</span>
          <span>Needed for: ${esc(gap.needed_for || "viewer validation")}</span>
        </div>
        <p class="muted-copy">Next data task: ${esc(gap.required_next_data || "not recorded")}</p>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderBoundaries(bundle) {
  const viewerLimitations = [
    "Local replay and review context only.",
    "The London, Chicago, and Helsinki cards are bounded source examples, not complete city coverage.",
    "The London mobility records are static infrastructure examples; they do not prove one lane-blockage incident or live disruption.",
    "Candidate-observation records come from local demo media or fixture evidence and remain candidate-only.",
    "Visual object records explain source identity context; they do not prove a certified or physically accurate twin.",
    "Human review is required before any future proposal lane could be considered.",
    "No production/public API, live monitoring, alerting, dispatch, routing/control, enforcement, official ticket, legal/certified conclusion, or automated action is created."
  ];
  return `<section id="review-boundaries" class="panel span-6" data-panel="review-boundaries">
    <p class="section-kicker">Review boundary</p>
    <h2>No approval, execution, or official finding</h2>
    <ul class="plain-list">
      ${listItems([
        "Local/replay review context only.",
        "No production or public API claim.",
        "No autonomous monitoring, alerting, dispatch, routing/control, enforcement, official ticket, legal/certified conclusion, or automated action.",
        "Human review is required before any future proposal lane could be considered."
      ])}
    </ul>
  </section>
  <section id="visible-limitations" class="panel span-6" data-panel="visible-limitations">
    <p class="section-kicker">Limitations ledger</p>
    <h2>What the viewer must keep in mind</h2>
    <ul class="plain-list">
      ${listItems(viewerLimitations)}
    </ul>
  </section>`;
}

function renderTechnicalDetails(bundle) {
  const payload = integratedPayload(bundle);
  return `<section id="technical-details-panel" class="panel span-12">
    <details id="technical-details">
      <summary>Show technical details / fixture refs / packet IDs</summary>
      <div class="technical-grid">
        <div>
          <h3>Scenario and entity refs</h3>
          <ul class="list">
            <li class="packet">${esc(bundle.scenario?.scenario_id)}</li>
            ${(bundle.scenario?.mobility_access_refs || []).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>Evidence refs</h3>
          <ul class="list">
            ${(bundle.evidence?.candidate_observation_refs || []).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}
            ${(bundle.evidence?.similar_case_refs || []).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}
            ${(bundle.evidence?.cascade_refs || []).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>Option and trace refs</h3>
          <ul class="list">
            ${(bundle.options?.candidate_options || []).map((option) => `<li class="packet">${esc(option.option_id)} | ${esc(option.option_type)} | ${esc(option.guardrail_result)}</li>`).join("")}
            ${(bundle.trace || []).map((stage) => `<li class="packet">${esc(stage.stage_name)} | ${esc(stage.execution_state)}</li>`).join("")}
          </ul>
        </div>
      </div>
      <div class="technical-grid">
        <div>
          <h3>Integrated bundle refs</h3>
          <ul class="list">
            ${(payload.technical_refs?.source_paths || []).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}
          </ul>
        </div>
      </div>
    </details>
  </section>`;
}

export function renderApp(bundle) {
  const streamPanel = renderOmniverseStreamPanel(bundle);
  const askV11HandoffPanel = hasAskV11HandoffBundle(bundle) ? renderAskV11Handoff(bundle) : "";
  if (hasProductModesBundle(bundle)) {
    return [streamPanel, askV11HandoffPanel, renderProductModes(bundle)].filter(Boolean).join("\n");
  }
  if (hasStoryQueueBundle(bundle)) {
    return [streamPanel, askV11HandoffPanel, renderStoryQueue(bundle)].filter(Boolean).join("\n");
  }
  if (hasStoryFirstBundle(bundle)) {
    return [streamPanel, askV11HandoffPanel, renderStoryFirst(bundle)].filter(Boolean).join("\n");
  }
  const payload = integratedPayload(bundle);
  return [
    streamPanel,
    askV11HandoffPanel,
    renderHero(bundle),
    renderTruthRegister(bundle),
    renderCoherenceVerdict(bundle),
    renderRecordSection("london-source-records", "London mobility records", "London mobility source examples", "These cards come from recovered London mobility-source rows. They provide context only; they do not prove live availability, a lane blockage, or one shared incident.", payload.situation_city_records),
    renderRecordSection("chicago-precedent-records", "Chicago precedent records", "Actual cross-city records used as memory context", "These cards show public Chicago records with source IDs and match reasons. They are contextual precedent, not instructions.", payload.similar_case_city_records),
    renderRecordSection("helsinki-visual-entity-records", "Helsinki visual-entity records", "Actual semantic building records for visual picking", "These cards connect source building records to visual object paths so a picked object can be explained without pretending it is a certified twin.", payload.visual_entity_city_records),
    renderRecordSection("candidate-observation-records", "Candidate observation records", "Local demo-media observations for review", "These records turn candidate-observation references into readable review cards. Missing time or location stays explicit; no city-source truth is claimed.", payload.media_observation_source_records),
    renderRecordSection("guardrail-refusal-records", "Guardrail refusal records", "Forbidden request shapes are blocked", "These records show the blocked request shape, the reason for refusal, and the no-action state in human-readable terms.", payload.guardrail_refusal_review_records),
    renderRecordSection("human-review-stop-records", "Human review-stop records", "Where review-only options stop", "These records show which choices require a human and confirm that no proposal approval or execution was created.", payload.human_review_stop_source_records),
    renderOptionReview(bundle),
    renderBlockers(bundle),
    renderBoundaries(bundle),
    renderTechnicalDetails(bundle)
  ].join("\n");
}

export function initializeDriveMode() {
  initializeOmniverseStreamPanel();
  initializeAskV11HandoffMode();
  const cards = Array.from(document.querySelectorAll(".queue-card, .answer-card, .brief-card, .check-card, .mode-output-card, .primary-story-card, .story-drilldown-panel, #london-source-records article, #chicago-precedent-records article, #helsinki-visual-entity-records article, #candidate-observation-records article, #guardrail-refusal-records article, #human-review-stop-records article, #review-choice-comparison article, #source-depth-blockers article"));
  if (!cards.length) return;
  let index = -1;
  const activate = (nextIndex) => {
    index = (nextIndex + cards.length) % cards.length;
    cards.forEach((card, cardIndex) => card.classList.toggle("active", cardIndex === index));
    cards[index].scrollIntoView({ behavior: "smooth", block: "center" });
  };
  document.querySelectorAll("[data-drive]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.drive;
      if (action === "start") activate(0);
      if (action === "prev") activate(index <= 0 ? cards.length - 1 : index - 1);
      if (action === "next") activate(index + 1);
      if (action === "why") document.querySelector("#current-ui-truth")?.scrollIntoView({ behavior: "smooth", block: "start" });
      if (action === "evidence") document.querySelector("#london-source-records")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  const sendD13BridgeSelection = async (card) => {
    const endpoint = window.localStorage.getItem("citybrain.d13.bridgeEndpoint")
      || (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost" ? "http://127.0.0.1:5188/citybrain/d13/selection" : "");
    if (!endpoint) return;
    const payload = {
      direction: "web_to_kit",
      command: "select",
      selection_id: `web-selection-${card.dataset.queueRank || "item"}-${Date.now()}`,
      entity_id: card.dataset.entityId || "",
      entity_label: card.dataset.entityLabel || card.querySelector("h3")?.textContent?.trim() || "",
      evidence_packet_ref: card.dataset.evidencePacketRef || "",
      limitations_ref: card.dataset.limitationsRef || "review_context_only_not_certified",
      execution_state: "not_executed",
      no_action_state: "no_action_taken",
      source_runtime_bundle_ref: "packages/fixtures/d9_product_modes/runtime_bundle/D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
      timestamp: new Date().toISOString()
    };
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      card.dataset.bridgePostStatus = response.ok ? "sent" : "failed";
    } catch {
      card.dataset.bridgePostStatus = "failed";
    }
  };
  document.querySelectorAll(".queue-card").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      sendD13BridgeSelection(card);
    });
  });

  const liveReceiptPanel = document.querySelector("#d13-live-web-kit-receipt");
  const liveReceiptSummary = document.querySelector("#d13-live-receipt-summary");
  const liveReceiptFields = document.querySelector("#d13-live-receipt-fields");
  if (liveReceiptPanel && liveReceiptSummary && liveReceiptFields) {
    const renderLiveReceipt = (event) => {
      const payload = event?.payload || {};
      const receipt = event?.receipt || {};
      if (!payload.payload_hash || !receipt.original_payload_hash) return;
      liveReceiptPanel.dataset.liveWebKitReceipt = "true";
      liveReceiptPanel.dataset.receivedBy = receipt.received_by || "web_ui";
      liveReceiptPanel.dataset.originalPayloadHash = receipt.original_payload_hash || "";
      liveReceiptPanel.dataset.entityId = payload.entity_id || "";
      liveReceiptPanel.dataset.executionState = receipt.execution_state || "not_executed";
      liveReceiptPanel.querySelector("h2").textContent = "Kit selection received in web";
      liveReceiptSummary.textContent = `Received ${payload.entity_label || payload.entity_id} from the Kit bridge. No official case or action was created.`;
      liveReceiptFields.innerHTML = [
        `Selection: ${payload.selection_id || "unknown"}`,
        `Entity: ${payload.entity_id || "unknown"}`,
        `Receipt: ${receipt.original_payload_hash || "missing"}`,
        `No action taken: ${String(receipt.no_action_taken ?? true)}`
      ].map((value) => `<span>${esc(value)}</span>`).join("");
    };
    const pollLiveReceipt = async () => {
      try {
        const response = await fetch(`/packages/fixtures/d13_live_web_kit_selection_receipt/runtime_overlay/D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json?ts=${Date.now()}`, { cache: "no-store" });
        if (response.ok) renderLiveReceipt(await response.json());
      } catch {
        // The receipt file is optional until the Kit bridge emits a selection.
      }
    };
    pollLiveReceipt();
    const interval = window.setInterval(pollLiveReceipt, 500);
    window.setTimeout(() => window.clearInterval(interval), 60000);
  }

  const logTarget = document.querySelector("#session-log-entries");
  if (!logTarget) return;
  const storageKey = "citybrain.operatorCockpit.localSessionLog";
  const stateTarget = document.querySelector("#current-local-state");
  const noteCountTarget = document.querySelector("#local-note-count");
  const summaryTarget = document.querySelector("#local-session-summary-stats");
  const exportPreviewTarget = document.querySelector("#local-export-preview");
  const noteInput = document.querySelector("#local-review-note");
  const statePanel = document.querySelector("#local-review-state-panel");
  const selectedItemTitle = statePanel?.dataset.selectedReviewItem || document.querySelector("#selected-review-item h2")?.textContent?.trim() || "Selected review item";
  const localStateLabels = {
    not_started: "Not started",
    in_review: "In review",
    needs_source: "Needs source",
    hold: "On hold",
    abstain: "Abstained",
    reviewed: "Reviewed locally",
    exported_locally: "Exported locally"
  };
  const readEntries = () => {
    try {
      return JSON.parse(window.localStorage.getItem(storageKey) || "[]");
    } catch {
      return [];
    }
  };
  const latestState = (entries) => [...entries].reverse().find((entry) => entry.local_state)?.local_state || statePanel?.dataset.currentLocalState || "not_started";
  const stateLabel = (state) => localStateLabels[state] || state.replace(/_/g, " ");
  const countVerb = (entries, verb) => entries.filter((entry) => entry.verb === verb).length;
  const readableSummary = (entries) => {
    if (!entries.length) return "Session summary: no local state changes yet. No official case or action was created.";
    const notes = countVerb(entries, "add_local_note");
    const asks = countVerb(entries, "ask") + countVerb(entries, "ask_about_item");
    const checks = countVerb(entries, "run_check");
    const briefs = countVerb(entries, "generate_brief");
    const abstentions = entries.filter((entry) => entry.local_state === "abstain").length;
    const statesChanged = entries.filter((entry) => entry.local_state).length;
    return `Session summary: ${entries.length} local review event${entries.length === 1 ? "" : "s"}, ${notes} note${notes === 1 ? "" : "s"}, ${asks} question${asks === 1 ? "" : "s"}, ${checks} check${checks === 1 ? "" : "s"}, ${briefs} brief${briefs === 1 ? "" : "s"}, ${statesChanged} state change${statesChanged === 1 ? "" : "s"}, ${abstentions} abstention${abstentions === 1 ? "" : "s"}. No official case or action was created.`;
  };
  const updateWorkspaceState = (entries) => {
    if (stateTarget) stateTarget.textContent = stateLabel(latestState(entries));
    if (noteCountTarget) noteCountTarget.textContent = String(countVerb(entries, "add_local_note"));
    if (summaryTarget) summaryTarget.textContent = readableSummary(entries);
  };
  const renderEntries = (entries) => {
    logTarget.innerHTML = entries.length
      ? entries.slice(-12).reverse().map((entry) => `<article class="mini-record" data-local-session-entry="true" data-mode-run-id="${esc(entry.mode_run_id)}" data-session-timestamp="${esc(entry.timestamp)}">
          <strong>${esc(entry.verb_label)} - saved locally</strong>
          <span>${esc(entry.note_text ? `Local note: ${entry.note_text}` : "No official case or action was created.")}</span>
        </article>`).join("")
      : `<article class="mini-record"><strong>No local review activity yet</strong><span>Use a review button to save a local note.</span></article>`;
    updateWorkspaceState(entries);
  };
  const entries = readEntries();
  renderEntries(entries);
  document.querySelectorAll("[data-review-verb]").forEach((button) => {
    button.addEventListener("click", () => {
      const verb = button.dataset.reviewVerb || "review";
      const modeRunId = button.dataset.modeRunId || button.closest("[data-mode-run-id]")?.dataset.modeRunId || "local-operator-session";
      const localState = button.dataset.reviewState || null;
      const noteText = button.dataset.localNoteButton ? (noteInput?.value || "").trim() || "Local review note saved." : "";
      const exportSlug = selectedItemTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "selected-review-item";
      const exportFilename = `LOCAL_REVIEW_ONLY_${exportSlug}_${new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z")}.md`;
      const entry = {
        verb,
        verb_label: button.dataset.stateLabel || button.textContent?.trim() || verb.replace(/_/g, " "),
        selected_item_title: selectedItemTitle,
        local_state: localState,
        note_text: noteText,
        export_filename: button.dataset.localExportButton ? exportFilename : null,
        mode_run_id: modeRunId,
        timestamp: new Date().toISOString(),
        boundary: "local_session_only_no_action"
      };
      const nextEntries = [...readEntries(), entry].slice(-50);
      window.localStorage.setItem(storageKey, JSON.stringify(nextEntries));
      if (noteText && noteInput) noteInput.value = "";
      if (button.dataset.localExportButton && exportPreviewTarget) {
        exportPreviewTarget.textContent = `Prepared local export preview: ${exportFilename}. No official case or action was created.`;
      }
      renderEntries(nextEntries);
    });
  });
}
