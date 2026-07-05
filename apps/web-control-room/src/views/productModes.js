const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

const REVIEW_VERBS = ["Open", "Ask", "Generate brief", "Run check", "Mark reviewed", "Add note"];
const SNAPSHOT_AS_OF = "2026-07-02";
const FALLBACK_RECORD_TIMES = {
  "TIMS-219173": "2026-07-01T22:21:20Z",
  "TIMS-210389": "2026-07-01T22:27:07Z",
  "87": "2026-07-02T07:03:38Z",
  "4463710": "2026-07-02T00:00:00Z",
  "uprn_context_profile:parcel:uk-london:uprn:5006082": "2026-06-26T07:02:39Z",
  "LON_D10_HARNESS_REPORT": "2026-06-26T07:02:39Z"
};

function operatorCopy(value) {
  return String(value ?? "")
    .replace(/no unsupported source is added by ASK/gi, "this answer adds no unsupported source")
    .replace(/brief:london-wood-lane/gi, "London Wood Lane review brief")
    .replace(/brief:ev-asset-87/gi, "EV asset 87 source brief")
    .replace(/brief:nyc-mvc-cascade/gi, "NYC MVC cascade review brief")
    .replace(/The local records does not/gi, "The local records do not")
    .replace(/Source-depth review item/gi, "Missing-evidence review item")
    .replace(/retained source refs/gi, "listed source records")
    .replace(/source refs/gi, "source records")
    .replace(/local source graph/gi, "local records")
    .replace(/source graph/gi, "local records")
    .replace(/graph\/source index/gi, "local source records")
    .replace(/D9 bundle/g, "local records")
    .replace(/The local records does not/gi, "The local records do not")
    .replace(/D9 AWB Check runtime/g, "this check board")
    .replace(/this runtime/gi, "this bundle")
    .replace(/not greened/gi, "not available");
}

function listItems(items, fallback = "None recorded.") {
  if (!items?.length) return `<li>${esc(fallback)}</li>`;
  return items.map((item) => `<li>${esc(operatorCopy(typeof item === "string" ? item : item.title || item.record_id || item.summary || "Recorded item"))}</li>`).join("");
}

function runtimeFrom(bundle) {
  return bundle.productModes?.bundle || null;
}

function operatorExtensionFrom(bundle) {
  return bundle.operatorCockpit?.intelligenceExtension || bundle.operatorCockpit?.runtimeExtension || null;
}

function operatorWorkflowFrom(bundle) {
  return bundle.operatorCockpit?.workflowExtension || null;
}

function d13LiveSeamFrom(bundle) {
  return bundle.spatialSeam?.liveSelectionEvent || null;
}

export function hasProductModesBundle(bundle) {
  const runtime = runtimeFrom(bundle);
  return Boolean(runtime?.product_mode_contract && runtime?.ask && runtime?.watch && runtime?.brief && runtime?.check);
}

function dedupeBy(items, keyFn) {
  const seen = new Set();
  const rows = [];
  for (const item of items || []) {
    const key = keyFn(item);
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(item);
  }
  return rows;
}

function sourceLabel(ref = {}) {
  const id = String(ref.record_id || "");
  const path = String(ref.path || "");
  if (id.startsWith("TIMS-")) return "TfL TIMS";
  if (id === "87" || id === "174" || path.includes("london_mobility_source_records")) return "London Datastore EV charging sites";
  if (id.includes("mvc_crash") || id.includes("4463710")) return "NYC collision source";
  if (id.includes("tax_lot")) return "NYC candidate tax-lot context";
  if (id.includes("fdny") || id.includes("engine_227")) return "NYC response-resource context";
  if (path.includes("lon_d10_planning_context")) return "London planning context";
  if (path.includes("chicago_similar_case")) return "Chicago source record";
  if (path.includes("helsinki")) return "Helsinki visual source";
  return ref.artifact_type ? String(ref.artifact_type).replace(/_/g, " ") : "Source record";
}

function recordTime(ref = {}) {
  return ref.record_time || ref.as_of || ref.last_modified || ref.fields?.last_modified || FALLBACK_RECORD_TIMES[ref.record_id] || `snapshot ${SNAPSHOT_AS_OF}`;
}

function operatorRecordLabel(ref = {}) {
  const id = String(ref.record_id || "");
  if (id.startsWith("TIMS-")) return id;
  if (id === "87" || id === "174" || /^\d+$/.test(id)) return id;
  if (id.includes("uprn_context_profile")) return "planning profile record";
  if (id.includes("pld_application_context_profile")) return "planning application profile";
  if (id.startsWith("edge:")) return "planning context edge sample";
  if (id.startsWith("LON_D10")) return "planning context report";
  if (id.includes(":")) return "source reference";
  return id || "record";
}

function sourceRows(refs = []) {
  const rows = dedupeBy(refs, (ref) => `${sourceLabel(ref)}:${ref.record_id}:${ref.title}`);
  if (!rows.length) return `<li>No source records on file.</li>`;
  return rows.map((ref) => `<li data-source-record-time="${esc(recordTime(ref))}">
    <strong>${esc(sourceLabel(ref))}</strong>
    <span>${esc(operatorRecordLabel(ref))} - ${esc(ref.title || "source record")}</span>
    <span class="source-date">Record time: ${esc(recordTime(ref))}</span>
  </li>`).join("");
}

function inspectorSourceRows(refs = []) {
  if (!refs.length) return `<li>No technical refs recorded.</li>`;
  return refs.map((ref) => `<li><strong>${esc(ref.record_id || ref.artifact_type || "source")}</strong><span>${esc(ref.title || "")}</span><span class="packet">${esc(ref.path || "")}</span></li>`).join("");
}

function entityById(runtime, entityId) {
  return (runtime.entity_index || []).find((entity) => entity.entity_id === entityId) || null;
}

function askByEntity(runtime, entityId) {
  return (runtime.ask?.sample_answers || []).find((answer) => answer.entity_id === entityId) || null;
}

function briefById(runtime, briefId) {
  return (runtime.brief?.packets || []).find((packet) => packet.brief_id === briefId) || null;
}

function investigationFor(extension, selected) {
  const key = selected.source_candidate_id || selected.watchItem?.candidate_id;
  return (extension?.selected_item_investigations || []).find((item) => item.source_candidate_id === key || item.candidate_id === key) || null;
}

function workflowStateFor(workflow, selected) {
  const key = selected.source_candidate_id || selected.watchItem?.candidate_id;
  return (workflow?.initial_review_states || []).find((item) => item.source_candidate_id === key || item.candidate_id === key) || null;
}

function queueProjection(runtime, extension = null) {
  const watchItems = runtime.watch?.review_queue || [];
  const byCandidate = Object.fromEntries(watchItems.map((item) => [item.candidate_id, item]));
  const extensionRows = extension?.ranked_queue_items || [];
  if (extensionRows.length) {
    return extensionRows
      .map((row) => ({
        ...row,
        watchItem: byCandidate[row.source_candidate_id] || null,
        selected: row.rank === 1,
        rankerId: row.ranker_id || "rank:city_situation@v1",
        modeRunId: row.mode_run_id || row.source_mode_run_id || byCandidate[row.source_candidate_id]?.mode_run_id || null,
        sourceRefs: row.source_refs || byCandidate[row.source_candidate_id]?.source_refs || []
      }))
      .filter((row) => row.watchItem || row.sourceRefs.length);
  }
  const rows = [
    {
      rank: 1,
      rankerId: "rank:city_situation@v1",
      kind: "city_situation_review_item",
      city: "London",
      place: "Wood Lane / Scrubbs Lane",
      title: "Review Wood Lane works near Scrubbs Lane EV access asset",
      shortTitle: "Wood Lane access review",
      evidence: "Source-backed with limits",
      uncertainty: "Nearby does not mean access was affected.",
      record_time: "2026-07-01T22:27:07Z",
      as_of: SNAPSHOT_AS_OF,
      rank_inputs: {
        recency_last_modified: "2026-07-01T22:27:07Z",
        source_severity: "Minimal",
        evidence_strength: "source_refs_present_proximity_only",
        corroborating_record_count: 3,
        uncertainty_class: "proximity_not_causality"
      },
      reviewVerb: "Review source link",
      watchItem: byCandidate["watch-candidate:lon:wood-lane-ev-access"],
      entityId: "corridor:uk-london:wood-lane-scrubbs-lane",
      briefId: "brief:london-wood-lane",
      selected: true,
    },
    {
      rank: 2,
      rankerId: "rank:city_situation@v1",
      kind: "city_situation_review_item",
      city: "NYC",
      place: "Howard Avenue / Brooklyn",
      title: "Review MVC crash 4463710 candidate asset context",
      shortTitle: "NYC MVC cascade review",
      evidence: "Candidate context only",
      uncertainty: "Possible nearby context is not certified affected-building truth or dispatch truth.",
      record_time: "2026-07-02T00:00:00Z",
      as_of: SNAPSHOT_AS_OF,
      rank_inputs: {
        recency_last_modified: "2026-07-02T00:00:00Z",
        source_severity: "context_only",
        evidence_strength: "candidate_asset_context",
        corroborating_record_count: 3,
        uncertainty_class: "candidate_not_certified_truth"
      },
      reviewVerb: "Compare source context",
      watchItem: byCandidate["watch-candidate:nyc:mvc-4463710-cascade"],
      entityId: "event:us-nyc:mvc_crash:4463710",
      briefId: "brief:nyc-mvc-cascade",
    },
    {
      rank: 3,
      rankerId: "rank:city_situation@v1",
      kind: "source_depth_review_item",
      city: "London",
      place: "Wood Lane / Scrubbs Lane",
      title: "Check missing evidence before any access-impact claim",
      shortTitle: "Wood Lane evidence check",
      evidence: "Needs more evidence",
      uncertainty: "The current packet cannot prove blockage, availability, or operational disruption.",
      record_time: "2026-07-01T22:27:07Z",
      as_of: SNAPSHOT_AS_OF,
      rank_inputs: {
        recency_last_modified: "2026-07-01T22:27:07Z",
        source_severity: "missing_impact_source",
        evidence_strength: "gap_detected",
        corroborating_record_count: 3,
        uncertainty_class: "source_depth_gap"
      },
      reviewVerb: "Run source-depth check",
      watchItem: byCandidate["watch-candidate:lon:wood-lane-source-gap"],
      entityId: "asset:uk-london:ev_charging_site:87",
      briefId: "brief:ev-asset-87",
    },
  ].filter((row) => row.watchItem);
  return rows;
}

function excludedQueueItems(runtime, extension = null) {
  const admitted = new Set(queueProjection(runtime, extension).map((row) => row.watchItem?.candidate_id || row.source_candidate_id));
  return (runtime.watch?.review_queue || [])
    .filter((item) => !admitted.has(item.candidate_id))
    .map((item) => ({
      candidate_id: item.candidate_id,
      reason: "Kept out of the main operator queue because it is a cutaway or internal/source-quality item, not a primary city situation.",
      query_id: item.query_id,
      mode_run_id: item.mode_run_id,
    }));
}

function humanUpdated(value = "") {
  const text = String(value);
  if (text.startsWith("2026-07-02")) return "Updated today";
  if (text.startsWith("2026-07-01")) return "Updated yesterday";
  const date = text.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  return date ? `Updated ${date}` : "Updated in this snapshot";
}

function operatorRankReason(item) {
  if (item.rank_reason) return operatorCopy(item.rank_reason);
  const candidate = item.source_candidate_id || item.watchItem?.candidate_id || "";
  if (candidate.includes("wood-lane-ev-access")) {
    return "nearby works and an EV access asset appear in the same review area; missing direct access-impact evidence is still visible";
  }
  if (candidate.includes("mvc-4463710")) {
    return "a collision record has nearby candidate context; this is context for review, not a certified affected-building finding";
  }
  if (candidate.includes("source-gap")) {
    return "the useful next step is checking whether stronger access-impact evidence exists";
  }
  return "source records and limits are present for human review";
}

function renderPatchHeader(runtime, queue) {
  return `<section id="operator-patch-board" class="operator-patch-board span-12" data-product-mode-console="true" data-brain-surface-default="operator-patch-board">
    <div class="patch-copy">
      <p class="eyebrow">Operator patch board</p>
      <h2>London and NYC review patch</h2>
      <p class="hero-line">Ranked city situations for human review, with cited answers, review briefs, and claim checks on the same board.</p>
      <div class="plain-status-row">
        <span class="status-pill safe">Local replay</span>
        <span class="status-pill safe">Review only - no action has been taken</span>
        <span class="status-pill">Snapshot: ${esc(SNAPSHOT_AS_OF)}</span>
        <span class="status-pill">Queue items: ${esc(queue.length)}</span>
        <span class="status-pill">Selected: ${esc(queue[0]?.shortTitle || "None")}</span>
      </div>
    </div>
    <div id="global-review-boundary" class="boundary-banner">
      <strong>Review boundary</strong>
      <p>This cockpit supports review, notes, cited answers, briefs, and checks. It does not dispatch, route, control, enforce, approve, create a case, certify a finding, publish an alert, or take action.</p>
    </div>
  </section>`;
}

function renderQueueCard(item) {
  const modeRun = item.modeRunId || item.watchItem?.mode_run_id || `operator-queue-${item.rank}`;
  const inputs = item.rank_inputs || {};
  const entityId = item.entityId || item.entity_id || item.source_candidate_id || item.watchItem?.entity_id || item.watchItem?.candidate_id || `queue-item-${item.rank}`;
  const evidencePacketRef = item.sourceRefs?.[0]?.record_id || item.watchItem?.source_refs?.[0]?.record_id || item.watchItem?.candidate_id || entityId;
  const recordCount = inputs.corroborating_record_count ?? item.sourceRefs?.length ?? item.watchItem?.source_refs?.length ?? 0;
  const updated = humanUpdated(item.record_time || inputs.recency_last_modified || recordTime(item.watchItem || {}));
  const needsReview = operatorCopy(item.operator_summary || item.evidence || "This item has source records that need a human look before any conclusion is used.");
  const rankedHere = `${updated} - ${recordCount} records on file - ${operatorRankReason(item)}`;
  return `<article class="queue-card ${item.selected ? "selected" : ""}" data-product-mode="WATCH" data-mode-run-id="${esc(modeRun)}" data-ranker-id="${esc(item.rankerId || "rank:city_situation@v1")}" data-rank-inputs="${esc(JSON.stringify(inputs))}" data-queue-rank="${esc(item.rank)}" data-queue-kind="${esc(item.kind)}" data-entity-id="${esc(entityId)}" data-entity-label="${esc(item.title)}" data-evidence-packet-ref="${esc(evidencePacketRef)}" data-limitations-ref="${esc(item.uncertainty || "review_context_only_not_certified")}">
    <span class="queue-rank">#${esc(item.rank)}</span>
    <div>
      <p class="record-type">${esc(item.city)} review item</p>
      <h3>${esc(item.title)}</h3>
      <p class="story-card-place">${esc(item.place)}</p>
      <dl class="operator-fields">
        <div><dt>Why this needs review</dt><dd>${esc(needsReview)}</dd></div>
        <div><dt>Why this is ranked here</dt><dd>${esc(rankedHere)}</dd></div>
        <div><dt>Records on file</dt><dd>${esc(recordCount)} source record${recordCount === 1 ? "" : "s"} connected to this review item.</dd></div>
        <div><dt>What may be nothing</dt><dd>${esc(item.uncertainty || "The local records may not prove a real-world impact.")}</dd></div>
        <div><dt>Suggested human check</dt><dd>${esc(item.reviewVerb)}</dd></div>
      </dl>
      <div class="operator-actions">
        ${REVIEW_VERBS.map((verb) => `<button type="button" data-review-verb="${esc(verb.toLowerCase().replace(/\s+/g, "_"))}" data-mode-run-id="${esc(modeRun)}">${esc(verb)}</button>`).join("")}
      </div>
    </div>
  </article>`;
}

function renderQueue(queue) {
  return `<section id="ranked-review-queue" class="panel span-5 operator-section">
    <p class="section-kicker">Ranked review queue</p>
    <h2>Review queue</h2>
    <p class="human-explain">Ranking is for review order only. It is not urgency, a finding, or an instruction.</p>
    <div class="queue-stack">
      ${queue.length ? queue.map(renderQueueCard).join("") : `<article id="empty-review-queue" class="empty-state"><strong>No review items in this bundle</strong><span>The cockpit loaded, but no admissible city-situation queue items were present.</span></article>`}
    </div>
  </section>`;
}

function renderReviewStatePanel(selected, workflow = null) {
  const state = workflowStateFor(workflow, selected) || {};
  const currentState = state.display_state || "Not started";
  const noteCount = state.local_note_count ?? 0;
  const selectedTitle = selected.shortTitle || selected.title || "Selected review item";
  return `<aside id="local-review-state-panel" class="review-state-panel" data-local-review-state-panel="true" data-current-local-state="${esc(state.local_state || "not_started")}" data-selected-review-item="${esc(selectedTitle)}">
    <p class="section-kicker">Local review state</p>
    <h3>Workspace state</h3>
    <p class="human-explain">These states are local review markers only. They do not close, approve, assign, dispatch, route, or create an official record.</p>
    <div class="state-status-grid">
      <div><span>Current state</span><strong id="current-local-state">${esc(currentState)}</strong></div>
      <div><span>Local notes</span><strong id="local-note-count">${esc(noteCount)}</strong></div>
    </div>
    <div class="state-button-row" aria-label="Local review state controls">
      <button type="button" data-review-verb="mark_needs_source" data-review-state="needs_source" data-state-label="Needs source">Needs source</button>
      <button type="button" data-review-verb="place_on_hold" data-review-state="hold" data-state-label="On hold">On hold</button>
      <button type="button" data-review-verb="abstain" data-review-state="abstain" data-state-label="Abstained">Abstain</button>
      <button type="button" data-review-verb="mark_reviewed" data-review-state="reviewed" data-state-label="Reviewed locally">Reviewed locally</button>
    </div>
    <label class="local-note-label" for="local-review-note">Local note</label>
    <textarea id="local-review-note" rows="3" placeholder="Add a local review note."></textarea>
    <div class="state-button-row">
      <button type="button" data-review-verb="add_local_note" data-local-note-button="true">Save local note</button>
      <button type="button" data-review-verb="export_local_summary" data-local-export-button="true" data-review-state="exported_locally" data-state-label="Exported locally">Export local summary</button>
    </div>
    <p id="local-session-summary-stats" class="human-explain">Session summary: no local state changes yet. No official case or action was created.</p>
    <p id="local-export-preview" class="human-explain">Local export filename will include LOCAL_REVIEW_ONLY.</p>
  </aside>`;
}

function renderSelectedItem(runtime, selected, extension = null, workflow = null) {
  const entity = entityById(runtime, selected.entityId) || {};
  const answer = askByEntity(runtime, selected.entityId) || {};
  const investigation = investigationFor(extension, selected);
  const refs = investigation?.records_on_file || selected.sourceRefs || selected.watchItem?.source_refs || entity.source_refs || answer.source_refs || [];
  const summary = investigation?.situation_summary || selected.operator_summary || selected.evidence || entity.summary || answer.summary || "Review item loaded from the local source bundle.";
  const knowns = investigation?.knowns || entity.knowns || answer.knowns;
  const unknowns = investigation?.unknowns || entity.unknowns || answer.unknowns;
  const cannotClaim = investigation?.cannot_claim || entity.cannot_claim || answer.cannot_claim;
  const suggestedQuestions = investigation?.suggested_questions || [];
  const briefSubjects = investigation?.brief_subjects || [];
  const checkFindings = investigation?.check_findings || [];
  const recall = investigation?.recall_availability;
  return `<section id="selected-review-item" class="panel span-7 operator-section" data-selected-city-item="${esc(selected.title)}">
    <p class="section-kicker">Selected item</p>
    <h2>${esc(selected.title)}</h2>
    <p class="human-explain">${esc(operatorCopy(summary))}</p>
    <div class="selected-workspace-grid">
      <div class="selected-facts">
        <div class="selected-grid">
          <div>
            <h3>Source records on file</h3>
            <ul class="plain-list source-list human-source-list">${sourceRows(refs)}</ul>
          </div>
          <div>
            <h3>Knowns</h3>
            <ul class="plain-list compact">${listItems(knowns)}</ul>
          </div>
          <div>
            <h3>Missing or uncertain</h3>
            <ul class="plain-list compact">${listItems(unknowns)}</ul>
          </div>
          <div>
            <h3>What this does not prove</h3>
            <ul class="plain-list compact">${listItems(cannotClaim)}</ul>
          </div>
          <div>
            <h3>Suggested questions</h3>
            <ul class="plain-list compact">${listItems(suggestedQuestions, "No supported questions for this item.")}</ul>
          </div>
          <div>
            <h3>Brief subjects</h3>
            <ul class="plain-list compact">${listItems(briefSubjects, "No brief subject on file.")}</ul>
          </div>
          <div>
            <h3>Checks on this item</h3>
            <ul class="plain-list compact">${listItems(checkFindings, "No check findings attached.")}</ul>
          </div>
          <div>
            <h3>Recall</h3>
            <p>${esc(operatorCopy(recall || "No field-matched recall is available for this item."))}</p>
          </div>
        </div>
      </div>
      ${renderReviewStatePanel(selected, workflow)}
    </div>
  </section>`;
}

function renderEntity360(runtime, extension = null) {
  const answer = extension?.entity_360_v2_answers?.[0] || (runtime.ask?.sample_answers || [])[0] || {};
  const refs = answer.source_refs || [];
  const coverage = answer.coverage_note || {};
  const operatorSummary = "This UPRN is linked to a London planning context area in the local records. No address was found in this cartridge. The link is based on a representative point, so treat it as contextual planning evidence, not certified parcel geometry.";
  const operatorKnowns = [
    "The local records contain a planning-context link for this UPRN.",
    "The link points to a London opportunity-area context record.",
    "The source method uses a representative point matched to an official context polygon.",
    "The record includes a confidence value for review, not certification."
  ];
  const relationshipItems = [
    "UPRN linked to a London planning context area.",
    "Representative point matched against an official context polygon."
  ];
  const operatorUnknowns = [
    "No address field was found for this UPRN in the local cartridge.",
    "This cartridge does not include enforcement or building-control records.",
    "Representative-point context is not certified parcel geometry."
  ];
  return `<article id="entity-360-answer" class="answer-card" data-product-mode="ASK" data-mode-run-id="${esc(answer.mode_run_id || "d9-ask-entity-360")}">
    <span class="record-type">Look up this entity</span>
    <h3>${esc(answer.entity_label || "UPRN 5006082 - address unavailable")}</h3>
    <p>${esc(operatorSummary)}</p>
    <div class="selected-grid">
      <div>
        <h3>What the local records say</h3>
        <ul class="plain-list compact">${listItems(operatorKnowns)}</ul>
      </div>
      <div>
        <h3>How it connects</h3>
        <ul class="plain-list compact">${listItems(relationshipItems)}</ul>
      </div>
      <div>
        <h3>Unknowns</h3>
        <ul class="plain-list compact">${listItems(operatorUnknowns)}</ul>
      </div>
      <div>
        <h3>Cannot claim</h3>
        <ul class="plain-list compact">${listItems(answer.cannot_claim)}</ul>
      </div>
    </div>
    <details class="evidence-details">
      <summary>Evidence details</summary>
      <ul class="plain-list source-list human-source-list">${sourceRows(refs)}</ul>
      <p class="coverage-note">Coverage note: ${esc(coverage.summary || "Corpus-scale counts are shown after the entity facts so they do not replace the answer.")}</p>
    </details>
  </article>`;
}

function renderAskPanel(runtime, selected, extension = null) {
  const selectedAnswer = askByEntity(runtime, selected.entityId) || (runtime.ask?.sample_answers || [])[1] || {};
  const selectedRefs = selectedAnswer.source_refs?.length ? selectedAnswer.source_refs : selected.sourceRefs || selected.watchItem?.source_refs || [];
  return `<section id="ask-selected-item" class="panel span-12 operator-section">
    <p class="section-kicker">Ask about the selected item</p>
    <h2>Bounded questions with citations</h2>
    <div class="ask-input-row">
      <input id="ask-question-input" data-ask-runtime="local-template" value="What do we know about the selected item?" aria-label="Ask about the selected review item">
      <button type="button" data-review-verb="ask_about_item" data-mode-run-id="${esc(selectedAnswer.mode_run_id || "d9-ask-selected-item")}">Ask</button>
    </div>
    <div class="prompt-chip-row">
      <span>What do we know?</span>
      <span>What source records support this?</span>
      <span>What is uncertain?</span>
      <span>What can we not claim?</span>
    </div>
    <div class="operator-two-col">
      ${renderEntity360(runtime, extension)}
      <article class="answer-card" data-product-mode="ASK" data-mode-run-id="${esc(selectedAnswer.mode_run_id || "d9-ask-selected")}">
        <span class="record-type">Selected item answer</span>
        <h3>${esc(selected.shortTitle)}</h3>
        <p>${esc(operatorCopy(selectedAnswer.summary || selected.why))}</p>
        <h3>Knowns</h3>
        <ul class="plain-list compact">${listItems(selectedAnswer.knowns)}</ul>
        <h3>Unknowns</h3>
        <ul class="plain-list compact">${listItems(selectedAnswer.unknowns)}</ul>
        <h3>Citations</h3>
        <ul class="plain-list source-list human-source-list">${sourceRows(selectedRefs)}</ul>
      </article>
    </div>
    <article class="refusal-card" data-product-mode="ASK" data-mode-run-id="d9-ask-unsupported-refusal-run-r1">
      <span class="record-type">Unsupported question behavior</span>
      <h3>Out-of-scope question refuses cleanly</h3>
      <p>If a question is outside the local records, the cockpit says it cannot answer from this bundle and gives a missing-evidence reason instead of improvising.</p>
    </article>
  </section>`;
}

function renderBriefSection(packet) {
  if (!packet) return "";
  return `<article class="brief-card" data-product-mode="BRIEF" data-mode-run-id="${esc(packet.mode_run_id)}">
    <span class="record-type">${packet.subject_kind === "non_story_entity" ? "Entity review brief" : "Situation review brief"}</span>
    <h3>${esc(packet.title)}</h3>
    <div class="brief-section-grid">
      <div><h3>Subject</h3><p>${esc(operatorCopy(packet.what_is_being_reviewed))}</p></div>
      <div><h3>Why it matters</h3><ul class="plain-list compact">${listItems(packet.what_is_connected)}</ul></div>
      <div><h3>Evidence</h3><ul class="plain-list source-list human-source-list">${sourceRows(packet.source_records)}</ul></div>
      <div><h3>Uncertainty</h3><ul class="plain-list compact">${listItems(packet.what_is_uncertain)}</ul></div>
      <div><h3>Review options</h3><ul class="plain-list compact">${listItems(packet.review_only_choices)}</ul></div>
      <div><h3>What this does not prove</h3><ul class="plain-list compact">${listItems(packet.what_cannot_be_claimed)}</ul></div>
    </div>
    <p class="human-explain">${esc(operatorCopy(packet.human_stop))}</p>
  </article>`;
}

function renderBriefPanel(runtime, selected) {
  const selectedBrief = briefById(runtime, selected.briefId);
  const entityBrief = briefById(runtime, "brief:ev-asset-87");
  return `<section id="review-brief-panel" class="panel span-7 operator-section">
    <p class="section-kicker">Review brief</p>
    <h2>Packet ready to copy into review notes</h2>
    ${renderBriefSection(selectedBrief)}
    ${selectedBrief?.brief_id === entityBrief?.brief_id ? "" : renderBriefSection(entityBrief)}
  </section>`;
}

function checkLabel(result) {
  const target = String(result.target_ref || "");
  if (target.includes("wood-lane")) return ["Cannot claim", "Nearby does not prove access impact."];
  if (target.includes("nyc")) return ["Possible nearby context", "Candidate tax-lot context is not certified affected-building truth."];
  if (target.includes("recall")) return ["Limited precedent", "Prior cases are visible only as context because match reasons are broad."];
  if (target.includes("DIFF")) return ["Not available yet", "Comparable source-record snapshots are not ready for live change review."];
  if (target.includes("PERCEPTION")) return ["Not in this cockpit", "Visual/perception mode is outside this review board."];
  if (target.includes("ev-asset-87")) return ["Missing evidence", "No live service availability or blockage source is present."];
  return ["Boundary check", result.reason || "Review the claim before using it."];
}

function renderCheckPanel(runtime) {
  const checks = runtime.check?.sample_results || [];
  return `<section id="claim-check-panel" class="panel span-5 operator-section">
    <p class="section-kicker">Checks</p>
    <h2>Be careful with these claims</h2>
    <div class="check-stack">
      ${checks.map((result) => {
        const [title, copy] = checkLabel(result);
        return `<article class="check-card" data-product-mode="CHECK" data-mode-run-id="${esc(result.mode_run_id)}">
          <span class="record-type">${esc(title)}</span>
          <h3>${esc(copy)}</h3>
          <p>${esc(operatorCopy(result.reason || "Review-only caution."))}</p>
        </article>`;
      }).join("")}
    </div>
  </section>`;
}

function renderSessionLog() {
  return `<section id="local-session-log" class="panel span-12 operator-section">
    <p class="section-kicker">Local session log</p>
    <h2>Review activity stays local</h2>
    <p class="human-explain">Buttons on this board can add a local review note for operator validation. No official case or action was created.</p>
    <div id="session-log-entries" class="session-log-entries" aria-live="polite">
      <article class="mini-record"><strong>No local review activity yet</strong><span>Use a review button to save a local note.</span></article>
    </div>
  </section>`;
}

function renderLiveSeamPanel(liveEvent = null) {
  const payload = liveEvent?.payload || {};
  const receipt = liveEvent?.receipt || {};
  const hasReceipt = Boolean(payload.payload_hash && receipt.original_payload_hash);
  return `<section id="d13-live-web-kit-receipt" class="panel span-12 operator-section live-seam-panel" data-live-web-kit-receipt="${hasReceipt ? "true" : "pending"}" data-received-by="${esc(receipt.received_by || "web_ui_pending")}" data-original-payload-hash="${esc(receipt.original_payload_hash || "")}" data-entity-id="${esc(payload.entity_id || "")}" data-execution-state="${esc(receipt.execution_state || "not_executed")}">
    <p class="section-kicker">Spatial selection receipt</p>
    <h2>${hasReceipt ? "Kit selection received in web" : "Waiting for a Kit selection receipt"}</h2>
    <p class="human-explain" id="d13-live-receipt-summary">${hasReceipt ? `Received ${payload.entity_label || payload.entity_id} from the Kit bridge. No official case or action was created.` : "The web cockpit will show a live receipt here when the Kit bridge emits a bounded selection event."}</p>
    <div class="record-meta" id="d13-live-receipt-fields">
      <span>Selection: ${esc(payload.selection_id || "pending")}</span>
      <span>Entity: ${esc(payload.entity_id || "pending")}</span>
      <span>Receipt: ${esc(receipt.original_payload_hash || "pending")}</span>
      <span>No action taken: ${esc(String(receipt.no_action_taken ?? true))}</span>
    </div>
  </section>`;
}

function renderInspector(runtime, queue, extension = null, workflow = null) {
  const allRefs = [
    ...(extension?.entity_360_v2_answers || []).flatMap((answer) => answer.source_refs || []),
    ...(extension?.ranked_queue_items || []).flatMap((item) => item.source_refs || []),
    ...(extension?.selected_item_investigations || []).flatMap((item) => item.records_on_file || []),
    ...(runtime.ask?.sample_answers || []).flatMap((answer) => answer.source_refs || []),
    ...(runtime.watch?.review_queue || []).flatMap((item) => item.source_refs || []),
    ...(runtime.brief?.packets || []).flatMap((packet) => packet.source_records || []),
  ];
  const excluded = excludedQueueItems(runtime, extension);
  return `<section id="operator-inspector" class="panel span-12 operator-section inspector-section">
    <details>
      <summary>Inspector: provenance, mode runs, paths, and audits</summary>
      <div class="technical-grid">
        <div>
          <h3>Mode run IDs</h3>
          <ul class="list packet">
            ${(extension?.entity_360_v2_answers || []).map((answer) => `<li>${esc(answer.template_call || answer.ask_query_id)} | ${esc(answer.mode_run_id)}</li>`).join("")}
            ${(runtime.ask?.sample_answers || []).map((answer) => `<li>${esc(answer.template_call || answer.ask_query_id)} | ${esc(answer.mode_run_id)}</li>`).join("")}
            ${(runtime.watch?.review_queue || []).map((item) => `<li>${esc(item.query_id)} | ${esc(item.candidate_id)} | ${esc(item.mode_run_id)}</li>`).join("")}
          </ul>
        </div>
        <div>
          <h3>Technical source refs</h3>
          <ul class="list packet">${inspectorSourceRows(dedupeBy(allRefs, (ref) => `${ref.path}:${ref.record_id}:${ref.title}`))}</ul>
        </div>
        <div>
          <h3>Main queue exclusions</h3>
          <ul class="list packet">${excluded.map((item) => `<li>${esc(item.candidate_id)} | ${esc(item.query_id)} | ${esc(item.reason)}</li>`).join("") || "<li>No exclusions recorded.</li>"}</ul>
        </div>
        <div>
          <h3>D11 local state contract</h3>
          <ul class="list packet">${(workflow?.review_state_contract?.allowed_states || []).map((state) => `<li>${esc(state)}</li>`).join("") || "<li>D11 workflow overlay not loaded.</li>"}</ul>
        </div>
      </div>
      <pre class="packet">${esc(JSON.stringify({
        source_runtime_bundle_ref: "packages/fixtures/d9_product_modes/runtime_bundle/D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
        projection: "operator_projection@v1",
        d11_projection: workflow ? "local_review_state_projection@r1" : "not_loaded",
        execution_state: runtime.execution_state,
        status: runtime.status,
        queue_items: queue.map((item) => ({ rank: item.rank, ranker_id: item.rankerId, title: item.title, source_candidate_id: item.watchItem?.candidate_id || item.source_candidate_id, mode_run_id: item.watchItem?.mode_run_id })),
      }, null, 2))}</pre>
    </details>
  </section>`;
}

function renderOperatorBoundaryDetails() {
  return `<section id="boundary-details" class="panel span-12 operator-section">
    <details>
      <summary>Review-only boundary details</summary>
      <ul class="plain-list compact">
        <li>No production or public API claim.</li>
        <li>No live monitoring or alerts.</li>
        <li>No dispatch, routing, control, enforcement, approval, official ticket, official case, legal finding, certified finding, or automated action.</li>
        <li>Open ASK router remains contract-only. Change review remains unavailable until comparable source snapshots exist.</li>
      </ul>
    </details>
  </section>`;
}

export function renderProductModes(bundle) {
  const runtime = runtimeFrom(bundle);
  if (!runtime) {
    return `<section id="operator-cockpit-load-failure" class="operator-patch-board span-12" data-product-mode-console="missing">
      <div class="patch-copy">
        <p class="eyebrow">Operator patch board</p>
        <h2>Runtime bundle unavailable</h2>
        <p class="hero-line">The cockpit did not load the D9 product-mode bundle, so it will not fabricate a queue or answer.</p>
      </div>
      <div class="boundary-banner">
        <strong>Review boundary</strong>
        <p>No action has been taken. Reload after the local fixture bundle is present.</p>
      </div>
    </section>`;
  }
  const extension = operatorExtensionFrom(bundle);
  const workflow = operatorWorkflowFrom(bundle);
  const liveSeam = d13LiveSeamFrom(bundle);
  const queue = queueProjection(runtime, extension);
  const selected = queue[0] || {};
  return [
    renderPatchHeader(runtime, queue),
    renderQueue(queue),
    queue.length ? renderSelectedItem(runtime, selected, extension, workflow) : "",
    queue.length ? renderAskPanel(runtime, selected, extension) : "",
    queue.length ? renderBriefPanel(runtime, selected) : "",
    renderCheckPanel(runtime),
    renderLiveSeamPanel(liveSeam),
    renderSessionLog(),
    renderOperatorBoundaryDetails(),
    renderInspector(runtime, queue, extension, workflow)
  ].join("\n");
}
