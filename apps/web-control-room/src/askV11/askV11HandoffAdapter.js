const asArray = (value) => Array.isArray(value) ? value : [];

const compact = (items) => asArray(items).filter((item) => item !== undefined && item !== null && item !== "");

export function uniqueItems(items) {
  return [...new Set(compact(items).map((item) => String(item)))];
}

function sourceLabel(source = {}) {
  return source.title || source.source_id || source.source_ref || source.label || "Source reference";
}

function verdictLabel(verdict = {}) {
  return compact([verdict.verdict, verdict.claim, verdict.reason]).join(" | ");
}

function checkLabel(check = {}) {
  return compact([check.check, check.status, check.reason]).join(" | ");
}

function downgradeLabel(downgrade = {}) {
  return compact([downgrade.claim, downgrade.downgraded_to, downgrade.reason]).join(" -> ");
}

function coverageLabel(note = {}) {
  return compact([note.summary, note.coverage_status, ...(note.limitations || [])]).join(" | ");
}

export function hasRawQueryKey(value) {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(hasRawQueryKey);
  return Object.entries(value).some(([key, nested]) => key === "raw_query" || hasRawQueryKey(nested));
}

export function normalizeAskV11Fixture(fixture = {}) {
  const payload = fixture.handoff_payload || {};
  const envelope = payload.flow_envelope || {};
  const boundary = payload.boundary_packet || {};
  const intent = payload.intent_packet || {};
  const contract = payload.execution_contract || {};
  const clarification = payload.clarification_packet || null;
  const evidence = payload.evidence_packet || {};
  const checkReport = payload.check_report || {};
  const answer = payload.answer_packet || {};
  const rendered = payload.rendered_response || null;
  const route = contract.route || {};
  const citations = asArray(answer.citations);
  const sourceRefs = asArray(evidence.source_refs).concat(asArray(contract.required_sources));
  const noData = Boolean(evidence.flags?.no_data || answer.coverage_note?.coverage_status === "no_data");
  const notExecuted = uniqueItems([
    ...asArray(answer.not_executed),
    ...asArray(evidence.not_executed),
    ...asArray(envelope.not_executed),
    ...asArray(clarification?.not_executed)
  ]);
  const validationErrors = uniqueItems([
    ...asArray(rendered?.validation_errors),
    ...asArray(rendered?.validation?.errors)
  ]);
  const boundaryRefusal = boundary.boundary && boundary.boundary !== "clear";

  return {
    scenarioId: fixture.scenario_id || "ask-v11-fixture",
    sourceBasis: asArray(fixture.source_basis),
    uiExpectations: fixture.ui_expectations || {},
    outcome: clarification ? "clarification" : boundaryRefusal ? "boundary_refusal" : rendered?.degraded ? "degraded_render" : rendered ? "answer" : "packet_state",
    flowEnvelope: envelope,
    boundary,
    intent,
    executionContract: contract,
    route,
    clarification,
    evidence,
    checkReport,
    answer,
    rendered,
    answerText: rendered?.text || "",
    degraded: Boolean(rendered?.degraded),
    validationErrors,
    knowns: asArray(answer.knowns),
    unknowns: asArray(answer.unknowns),
    cannotClaim: asArray(answer.cannot_claim),
    citations,
    sourceRefs,
    coverageNote: answer.coverage_note || null,
    safeNextLooks: asArray(answer.safe_next_looks),
    notExecuted,
    checks: asArray(checkReport.checks),
    verdicts: asArray(checkReport.verdicts),
    claimDowngrades: asArray(checkReport.claim_downgrades),
    abstains: asArray(checkReport.abstains),
    contradictions: asArray(checkReport.contradictions),
    staleness: asArray(checkReport.staleness),
    coverageLimits: asArray(checkReport.coverage_limits),
    bindingFindings: asArray(checkReport.binding_findings),
    overallClaimability: checkReport.overall_claimability || "",
    traceHops: asArray(envelope.trace_hops),
    stageFailures: asArray(envelope.stage_failures),
    packetRefs: envelope.packet_refs || {},
    noData,
    hasRawQuery: hasRawQueryKey(payload),
    labels: {
      checks: asArray(checkReport.checks).map(checkLabel),
      verdicts: asArray(checkReport.verdicts).map(verdictLabel),
      claimDowngrades: asArray(checkReport.claim_downgrades).map(downgradeLabel),
      coverageLimits: asArray(checkReport.coverage_limits).map(coverageLabel),
      citations: citations.map((citation) => compact([citation.citation_id, citation.source_ref, citation.label]).join(" | ")),
      sourceRefs: sourceRefs.map(sourceLabel),
      trace: asArray(envelope.trace_hops).map((hop) => compact([hop.stage_id, hop.gate_id, hop.status]).join(" | "))
    }
  };
}

export function normalizeAskV11FixtureSet(bundleOrFixtureSet = {}) {
  const fixtureSet = bundleOrFixtureSet.askV11?.handoffFixtures || bundleOrFixtureSet;
  return asArray(fixtureSet.fixtures).map(normalizeAskV11Fixture);
}

export function askV11FixtureScenarioIds(bundleOrFixtureSet = {}) {
  return normalizeAskV11FixtureSet(bundleOrFixtureSet).map((fixture) => fixture.scenarioId);
}
