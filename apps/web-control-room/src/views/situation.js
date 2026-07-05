const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderSituation(bundle) {
  const counts = bundle.oneTruth.authoritative_counts;
  return `<section id="situation" class="panel span-8" data-panel="situation" data-scenario-state-ref="${esc(bundle.oneTruth.scenario_state_ref)}">
    <h2>Situation overview</h2>
    <p class="claim-line" data-assert="hero-spine">${esc(bundle.scenario.hero_spine)}</p>
    <div class="metric-grid">
      <div class="metric"><span>Execution state</span><strong data-assert="execution-state">${esc(bundle.review.execution_state)}</strong></div>
      <div class="metric"><span>Reviewed option sets</span><strong data-assert="reviewed-option-sets-count">${counts.reviewed_option_set_count}</strong></div>
      <div class="metric"><span>Candidate options</span><strong data-assert="candidate-options-count">${counts.candidate_option_count}</strong></div>
      <div class="metric"><span>Trace stages</span><strong data-assert="trace-stage-count">${counts.operator_trace_stage_count}</strong></div>
    </div>
    <p id="mobility-source-fusion">Mobility multi-source fusion is projected from certified Mobility Access, D7, cascade, similar-case, trace, and Track D roots.</p>
    <p id="mobility-cascade">Mobility corridor cascade remains evidence/context only with no action authority.</p>
  </section>`;
}
