import { normalizeAskV11FixtureSet } from "../askV11/askV11HandoffAdapter.js";

const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function titleize(value) {
  return String(value || "ASK scenario").replace(/_/g, " ");
}

function listItems(items, fallback = "None recorded.", attrs = "") {
  if (!items?.length) return `<li ${attrs}>${esc(fallback)}</li>`;
  return items.map((item) => `<li ${attrs}>${esc(typeof item === "string" ? item : JSON.stringify(item))}</li>`).join("");
}

function miniRecords(items, fallback, mapper, attrs = "") {
  if (!items?.length) return `<article class="mini-record" ${attrs}><strong>${esc(fallback)}</strong></article>`;
  return items.map((item) => mapper(item)).join("");
}

function renderListSection(title, items, sectionName, fallback = "None recorded.") {
  return `<div class="ask-v11-card" data-ui-section="${esc(sectionName)}">
    <h3>${esc(title)}</h3>
    <ul class="plain-list compact">${listItems(items, fallback)}</ul>
  </div>`;
}

function renderCitations(model) {
  const citationCards = model.citations.map((citation) => `<article class="mini-record" data-ui-section="citation">
    <strong>${esc(citation.label || citation.citation_id || "Citation")}</strong>
    <span>${esc(citation.source_ref || "source_ref missing")}</span>
    <span class="packet">${esc((citation.evidence_refs || []).join(", "))}</span>
  </article>`);
  const sourceCards = model.sourceRefs.map((source) => `<article class="mini-record" data-ui-section="source_ref">
    <strong>${esc(source.title || source.source_id || "Source ref")}</strong>
    <span>${esc(source.source_id || source.source_ref || "source id missing")}</span>
    <span>${esc(source.claim_boundary || source.source_type || "retained source reference")}</span>
    ${source.uri ? `<span class="packet">${esc(source.uri)}</span>` : ""}
  </article>`);
  return `<div class="ask-v11-card" data-ui-section="citations">
    <h3>Citations and source refs</h3>
    <div class="record-list">${citationCards.join("") || `<article class="mini-record"><strong>No citations recorded</strong></article>`}</div>
    <div class="record-list">${sourceCards.join("") || `<article class="mini-record"><strong>No source refs recorded</strong></article>`}</div>
  </div>`;
}

function renderCheckDetails(model) {
  if (model.clarification) return "";
  const hasCheckContent = model.checks.length
    || model.verdicts.length
    || model.claimDowngrades.length
    || model.abstains.length
    || model.contradictions.length
    || model.staleness.length
    || model.overallClaimability;
  if (!hasCheckContent) return "";
  const checks = model.checks.map((check) => `<article class="mini-record" data-ui-section="check_detail">
    <strong>${esc(check.check || "check")}: ${esc(check.status || "status missing")}</strong>
    <span>${esc(check.reason || "No reason recorded.")}</span>
    <span class="packet">${esc((check.refs || []).join(", "))}</span>
  </article>`);
  const verdicts = model.verdicts.map((verdict) => `<article class="mini-record" data-ui-section="claimability">
    <strong>${esc(verdict.verdict || "verdict")}</strong>
    <span>${esc(verdict.claim || "claim not recorded")}</span>
    <span>${esc(verdict.reason || "No reason recorded.")}</span>
  </article>`);
  const downgrades = model.claimDowngrades.map((downgrade) => `<article class="mini-record warning-card" data-ui-section="downgrade">
    <strong>${esc(downgrade.claim || "claim")} -> ${esc(downgrade.downgraded_to || "downgraded")}</strong>
    <span>${esc(downgrade.reason || "No downgrade reason recorded.")}</span>
  </article>`);
  const abstains = model.abstains.map((abstain) => `<article class="mini-record danger-mini" data-ui-section="abstain"><strong>Abstain</strong><span>${esc(abstain.reason)}</span></article>`);
  const contradictions = model.contradictions.map((item) => `<article class="mini-record danger-mini" data-ui-section="contradiction"><strong>Contradiction</strong><span>${esc(item.reason)}</span></article>`);
  const staleness = model.staleness.map((item) => `<article class="mini-record warning-card" data-ui-section="staleness"><strong>Staleness</strong><span>${esc(item.reason)}</span></article>`);

  return `<div class="ask-v11-card" data-ui-section="check_details">
    <h3>CHECK details</h3>
    <p class="human-explain">Claimability: ${esc(model.overallClaimability || "not recorded")}</p>
    <div class="record-list">
      ${checks.join("") || `<article class="mini-record"><strong>No check findings recorded</strong></article>`}
      ${verdicts.join("")}
      ${downgrades.join("")}
      ${abstains.join("")}
      ${contradictions.join("")}
      ${staleness.join("")}
    </div>
  </div>`;
}

function renderTrace(model) {
  const traceCards = model.traceHops.map((hop) => `<div class="stage" data-ui-section="trace_hop" data-stage="${esc(hop.stage_id)}">
    <strong>${esc(hop.stage_id)} ${esc(hop.status || "")}</strong>
    <span>${esc(hop.gate_id || "gate not recorded")}</span>
    <span class="packet">${esc([...(hop.input_packet_refs || []), ...(hop.output_packet_refs || [])].join(" -> "))}</span>
  </div>`);
  const failureCards = model.stageFailures.map((failure) => `<article class="mini-record danger-mini" data-ui-section="stage_failure">
    <strong>${esc(failure.stage_id)} ${esc(failure.failure_class)}</strong>
    <span>${esc(failure.reason)}</span>
  </article>`);
  return `<div class="ask-v11-card ask-v11-wide" data-ui-section="trace">
    <h3>Trace and packet refs</h3>
    <div class="trace-grid">${traceCards.join("") || `<div class="stage"><strong>No trace hops recorded</strong></div>`}</div>
    <div class="record-list">${failureCards.join("")}</div>
    <pre class="packet">${esc(JSON.stringify(model.packetRefs, null, 2))}</pre>
  </div>`;
}

function renderClarification(model) {
  if (!model.clarification) return "";
  return `<div class="ask-v11-card warning-card" data-ui-section="clarification">
    <h3>Clarification required</h3>
    <p>${esc(model.clarification.question)}</p>
    <p class="packet">Target field: ${esc(model.clarification.target_field || "not recorded")}</p>
    <ul class="plain-list compact">${listItems(model.clarification.candidates, "No candidates recorded.")}</ul>
  </div>`;
}

function renderBoundaryRefusal(model) {
  const boundaryRefusal = model.boundary?.boundary && model.boundary.boundary !== "clear";
  if (!boundaryRefusal && model.route?.kind !== "refuse") return "";
  return `<div class="ask-v11-card danger-card" data-ui-section="boundary_refusal">
    <h3>Boundary / refusal</h3>
    <p>Boundary: ${esc(model.boundary.boundary || "not recorded")}</p>
    <p>Route: ${esc(model.route?.kind || "not recorded")}</p>
    <ul class="plain-list compact">${listItems(model.boundary.reason_codes, "No reason codes recorded.")}</ul>
  </div>`;
}

function renderDegraded(model) {
  if (!model.degraded) return "";
  return `<div class="ask-v11-card danger-card" data-ui-section="degraded_render">
    <h3>Degraded render</h3>
    <p>${esc(model.answerText)}</p>
    <ul class="plain-list compact">${listItems(model.validationErrors, "No validation errors recorded.")}</ul>
  </div>`;
}

function renderCoverage(model) {
  const note = model.coverageNote;
  return `<div class="ask-v11-card" data-ui-section="coverage">
    <h3>Coverage</h3>
    <p>${esc(note?.summary || "No coverage note recorded.")}</p>
    <p class="packet">${esc(note?.coverage_status || (model.noData ? "no_data" : "coverage status not recorded"))}</p>
    <ul class="plain-list compact">${listItems(note?.limitations, "No coverage limitations recorded.")}</ul>
  </div>`;
}

function renderScenario(model, index) {
  return `<section id="ask-v11-${esc(model.scenarioId)}" class="panel span-12 ask-v11-scenario" data-ask-v11-scenario="${esc(model.scenarioId)}" data-ask-v11-outcome="${esc(model.outcome)}" data-ask-v11-no-data="${model.noData ? "true" : "false"}" data-ask-v11-degraded="${model.degraded ? "true" : "false"}" data-ask-v11-active="${index === 0 ? "true" : "false"}">
    <div class="drive-header">
      <div>
        <p class="section-kicker">ASK v1.1 packet fixture</p>
        <h2>${esc(titleize(model.scenarioId))}</h2>
        <p class="human-explain">Local/demo packet handoff. The app renders packet fields only and does not reinterpret user text or fetch citation URLs.</p>
      </div>
      <div class="plain-status-row">
        <span class="status-pill safe">Outcome: ${esc(model.outcome)}</span>
        <span class="status-pill">${model.noData ? "No data visible" : "Evidence state visible"}</span>
        <span class="status-pill">${model.degraded ? "Render degraded" : "Render safe"}</span>
      </div>
    </div>
    <div class="ask-v11-grid">
      <article class="ask-v11-card ask-v11-wide" data-ui-section="answer_panel">
        <h3>Answer</h3>
        <pre class="ask-v11-answer-text">${esc(model.answerText || (model.clarification ? model.clarification.question : "No final answer rendered for this route."))}</pre>
      </article>
      ${renderListSection("Knowns", model.knowns, "knowns", "No supported knowns recorded.")}
      ${renderListSection("Unknowns", model.unknowns, "unknowns", "No unknowns recorded.")}
      ${renderListSection("Cannot claim", model.cannotClaim, "cannot_claim", "No cannot-claim entries recorded.")}
      ${renderCoverage(model)}
      ${renderCitations(model)}
      ${renderCheckDetails(model)}
      ${renderListSection("Safe next looks", model.safeNextLooks, "safe_next_looks", "No safe next looks recorded.")}
      ${renderListSection("Not executed", model.notExecuted, "not_executed", "No not-executed entries recorded.")}
      ${renderClarification(model)}
      ${renderBoundaryRefusal(model)}
      ${renderDegraded(model)}
      ${renderTrace(model)}
    </div>
  </section>`;
}

export function hasAskV11HandoffBundle(bundle) {
  return normalizeAskV11FixtureSet(bundle).length > 0;
}

export function renderAskV11Handoff(bundle) {
  const fixtures = normalizeAskV11FixtureSet(bundle);
  if (!fixtures.length) return "";
  return `<section id="ask-v11-handoff" class="panel span-12 ask-v11-handoff" data-ask-v11-handoff="true" data-fixture-count="${fixtures.length}">
    <p class="section-kicker">ASK v1.1 local handoff</p>
    <h2>Sealed packet fixtures are visible in the cockpit</h2>
    <p class="human-explain">This local/demo panel consumes ASK packet fixture DTOs. It does not call ASK runtime, fetch external URLs, or create official action controls.</p>
    <nav class="prompt-chip-row" aria-label="ASK v1.1 fixture scenarios">
      ${fixtures.map((fixture) => `<a class="story-nav-link secondary" href="#ask-v11-${esc(fixture.scenarioId)}" data-ask-v11-scenario-link="${esc(fixture.scenarioId)}">${esc(titleize(fixture.scenarioId))}</a>`).join("")}
    </nav>
  </section>
  ${fixtures.map(renderScenario).join("\n")}`;
}

export function initializeAskV11HandoffMode(root = document) {
  if (!root?.querySelectorAll) return;
  const scenarios = Array.from(root.querySelectorAll("[data-ask-v11-scenario]"));
  root.querySelectorAll("[data-ask-v11-scenario-link]").forEach((link) => {
    link.addEventListener("click", () => {
      const scenarioId = link.dataset.askV11ScenarioLink;
      scenarios.forEach((scenario) => {
        scenario.dataset.askV11Active = scenario.dataset.askV11Scenario === scenarioId ? "true" : "false";
      });
    });
  });
}
