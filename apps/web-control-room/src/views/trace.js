const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderTrace(bundle) {
  return `<section id="trace" class="panel span-12" data-panel="trace">
    <h2>Governed 9-stage trace</h2>
    <div class="trace-grid">
      ${bundle.trace.map((stage) => `<div class="stage ${stage.stage_name === "SYNTHESIZE" ? "synthesize" : ""}" data-stage="${esc(stage.stage_name)}">
        <strong>${stage.stage_index}. ${esc(stage.stage_name)}</strong>
        <span>${stage.narration_permitted ? "single narration boundary" : "deterministic/review stage"}</span>
        <span>${esc(stage.execution_state)}</span>
      </div>`).join("")}
    </div>
  </section>`;
}
