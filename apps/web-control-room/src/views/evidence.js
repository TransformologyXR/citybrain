const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderEvidence(bundle) {
  return `<section id="evidence" class="panel span-4" data-panel="evidence">
    <h2>Evidence candidates</h2>
    <div class="metric-grid">
      <div class="metric"><span>D7 candidate observations</span><strong data-assert="d7-candidate-observations-count">${bundle.evidence.candidate_observation_count}</strong></div>
      <div class="metric"><span>Similar cases</span><strong data-assert="similar-case-count">${bundle.evidence.similar_case_count}</strong></div>
    </div>
    <p id="d7-evidence">D7 observations are candidate observations, not findings.</p>
    <p id="similar-cases">Cross-city memory provides ${bundle.evidence.similar_case_count} contextual similar cases.</p>
    <p id="uncertainty-affordance" class="warning">Honest uncertainty is visible: evidence confidence is qualitative and limitations stay attached.</p>
    <ul class="list">${bundle.evidence.candidate_observation_refs.slice(0, 6).map((ref) => `<li class="packet">${esc(ref)}</li>`).join("")}</ul>
  </section>`;
}
