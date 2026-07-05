const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderCapture(bundle) {
  const demonstrable = bundle.scoreboard.rows.filter((row) => row.score_status === "demonstrable");
  return `<section id="capture" class="panel span-12" data-panel="capture">
    <h2>Capture readiness</h2>
    <p class="claim-line">${demonstrable.length} demonstrable moments have render homes; media capture is not claimed here.</p>
    <div class="list">${bundle.scoreboard.rows.map((row) => `<div class="moment-row" data-moment-id="${esc(row.moment_id)}">
      <strong>${esc(row.moment_id)} ${esc(row.title)}</strong>
      <span>${esc(row.score_status)}</span>
    </div>`).join("")}</div>
  </section>`;
}
