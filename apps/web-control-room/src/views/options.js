const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderOptions(bundle) {
  const axes = bundle.options.shared_axis_tradeoff_affordance.axes;
  const options = bundle.options.candidate_options;
  return `<section id="options" class="panel span-8" data-panel="options">
    <h2>Option-set comparison</h2>
    <p class="claim-line">${bundle.options.reviewed_option_set_count} reviewed option sets / ${bundle.options.candidate_option_count} candidate options / ${esc(bundle.options.execution_state)}</p>
    <div id="shared-axis-tradeoff" class="axis-grid">
      ${axes.map((axis) => `<div class="axis"><span>Shared axis</span><strong>${esc(axis)}</strong></div>`).join("")}
    </div>
    <ul class="list">
      ${options.map((option) => `<li class="packet" data-option-id="${esc(option.option_id)}">
        <strong>${esc(option.option_role)}</strong>
        <span>${esc(option.option_type)} | ${esc(option.eligibility_state)} | ${esc(option.execution_state)}</span>
      </li>`).join("")}
    </ul>
  </section>`;
}
