const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderLimitations(bundle) {
  return `<section id="limitations" class="panel span-6" data-panel="limitations">
    <h2>Limitations and claim labels</h2>
    <p id="limitation-ledger" class="claim-line">Limitations remain visible; M04/M05 are documented partial.</p>
    <ul class="list">${bundle.limitations.limitations.slice(0, 9).map((item) => `<li class="packet">${esc(item)}</li>`).join("")}</ul>
    <div class="toolbar">${bundle.labels.labels.map((label) => `<span class="chip">${esc(label.text)}</span>`).join("")}</div>
  </section>`;
}
