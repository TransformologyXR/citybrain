const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

export function renderTrackD(bundle) {
  return `<section id="track-d" class="panel span-6" data-panel="track-d">
    <h2>Track D promotion stop</h2>
    <p id="track-d-stop" class="claim-line">Track D remains authoritative. Approved proposal created: ${bundle.trackD.approved_proposal_created}</p>
    <p id="guardrail-refusal" class="danger">Forbidden action-shaped commands are rejected; eligible packets stay human-review only.</p>
    <div class="metric-grid">
      <div class="metric"><span>Eligible packets</span><strong data-assert="eligible-track-d-packets-count">${bundle.trackD.eligible_packet_count}</strong></div>
      <div class="metric"><span>Non-promotion packets</span><strong>${bundle.trackD.non_promotion_packet_count}</strong></div>
    </div>
    <ul class="list">${bundle.trackD.packets.slice(0, 7).map((packet) => `<li class="packet">${esc(packet.panel_packet_id)} | ${esc(packet.guardrail_result)} | ${esc(packet.execution_state)}</li>`).join("")}</ul>
  </section>`;
}
