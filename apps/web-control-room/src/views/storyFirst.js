const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function listItems(items, fallback = "None recorded.") {
  if (!items?.length) return `<li>${esc(fallback)}</li>`;
  return items.map((item) => `<li>${esc(item)}</li>`).join("");
}

function chipItems(items, fallback = "None recorded") {
  if (!items?.length) return `<span class="chip muted">${esc(fallback)}</span>`;
  return items.map((item) => `<span class="chip">${esc(item)}</span>`).join("");
}

function storyBundleFrom(bundle) {
  return bundle.storyFirst?.bundle || null;
}

function scenarioLayerFrom(bundle) {
  return bundle.storyFirst?.scenarioLayer || null;
}

export function hasStoryFirstBundle(bundle) {
  const scenarioLayer = scenarioLayerFrom(bundle);
  if (scenarioLayer?.scenario?.story_id || scenarioLayer?.selected_story?.story_id) return true;
  const storyBundle = storyBundleFrom(bundle);
  return Boolean(storyBundle?.selected_story?.story_id || storyBundle?.story_id);
}

function selectedStory(bundle) {
  const scenarioLayer = scenarioLayerFrom(bundle);
  if (scenarioLayer?.scenario) return scenarioLayer.scenario;
  if (scenarioLayer?.selected_story) return scenarioLayer.selected_story;
  const storyBundle = storyBundleFrom(bundle);
  return storyBundle.selected_story || storyBundle;
}

function renderRecord(record) {
  const fields = record.fields || {};
  const fieldRows = Object.entries(fields)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `<span>${esc(key.replace(/_/g, " "))}: ${esc(value)}</span>`)
    .join("");
  return `<article class="fact-card story-record-card" data-record-id="${esc(record.source_record_id)}" data-card-classification="${esc(record.card_classification)}">
    <span class="record-type">${esc(record.card_classification || "SOURCE RECORD")}</span>
    <h3>${esc(record.title)}</h3>
    <p>${esc(record.summary)}</p>
    <div class="record-meta">
      <span>Dataset: ${esc(record.source_dataset)}</span>
      <span>Record ID: ${esc(record.source_record_id)}</span>
      ${fieldRows}
    </div>
    <div class="chip-row">${chipItems(record.evidence_links, "Evidence reference retained")}</div>
  </article>`;
}

function renderBeat(beat, index) {
  return `<article class="story-beat-card" data-beat-index="${index + 1}">
    <span class="step-number">${index + 1}</span>
    <h3>${esc(beat.title)}</h3>
    <p>${esc(beat.viewer_copy)}</p>
    <div class="record-meta">
      <span>Records: ${esc((beat.source_record_ids || []).join(", "))}</span>
      <span>Status: ${esc(beat.status_or_time || "record status retained in source")}</span>
    </div>
    <p class="muted-copy">Limit: ${esc(beat.limitation)}</p>
  </article>`;
}

function renderStoryHero(story) {
  return `<section id="story-first-hero" class="hero-panel story-first-hero span-12" data-panel="story-first-hero">
    <div class="hero-copy">
      <p class="eyebrow">${esc(story.scenario_layer_validated ? "Validated bounded scenario layer" : "Story-first source record demo")}</p>
      <h2>${esc(story.scene_title)}</h2>
      <p class="hero-line">${esc(story.viewer_summary)}</p>
      <div class="plain-status-row">
        <span class="status-pill safe">Place: ${esc(story.place_or_corridor)}</span>
        <span class="status-pill safe">City: ${esc(story.city)}</span>
        <span class="status-pill">Status/time: ${esc(story.date_time_or_status)}</span>
        <span class="status-pill safe">No action has been taken</span>
      </div>
    </div>
    <div class="hero-note">
      <strong>Why this matters</strong>
      <p>${esc(story.why_this_is_non_obvious)}</p>
      <p class="muted-copy">${esc(story.primary_limitation)}</p>
    </div>
  </section>`;
}

function renderMapAnchor(story) {
  const geo = story.map_anchor || {};
  return `<section id="story-map-anchor" class="panel span-5" data-panel="story-map-anchor">
    <p class="section-kicker">Map / visual anchor</p>
    <h2>${esc(geo.label || story.place_or_corridor)}</h2>
    <div class="story-map-card" aria-label="source location preview">
      <div class="map-grid-lines"></div>
      <div class="map-pin primary-pin"></div>
      <div class="map-pin secondary-pin"></div>
      <span class="map-label">${esc(geo.label || "source location")}</span>
    </div>
    <div class="record-meta">
      <span>Latitude: ${esc(geo.latitude)}</span>
      <span>Longitude: ${esc(geo.longitude)}</span>
      <span>Geometry: ${esc(geo.geometry_status || "source point")}</span>
    </div>
  </section>`;
}

function renderEvidenceStack(story) {
  return `<section id="story-evidence-stack" class="panel span-7" data-panel="story-evidence-stack">
    <p class="section-kicker">Evidence stack</p>
    <h2>Actual records, not architecture counters</h2>
    <div class="record-grid two-col">
      ${(story.records || []).map(renderRecord).join("")}
    </div>
  </section>`;
}

function renderConnection(story) {
  return `<section id="story-citybrain-connection" class="panel span-12" data-panel="story-citybrain-connection">
    <p class="section-kicker">CityBrain connection</p>
    <h2>Why CityBrain linked these records</h2>
    <div class="record-grid three-col">
      ${(story.connection_points || []).map((point) => `<article class="fact-card">
        <span class="record-type">${esc(point.kind)}</span>
        <h3>${esc(point.title)}</h3>
        <p>${esc(point.summary)}</p>
        <p class="muted-copy">${esc(point.limitation)}</p>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderHumanReview(story) {
  return `<section id="story-human-review" class="panel span-6" data-panel="story-human-review">
    <p class="section-kicker">Human review choices</p>
    <h2>What the viewer can safely do</h2>
    <ul class="plain-list">
      ${listItems(story.human_review_choices)}
    </ul>
  </section>
  <section id="story-stop-boundary" class="panel span-6" data-panel="story-stop-boundary">
    <p class="section-kicker">Stop boundary</p>
    <h2>No approval, execution, or official finding</h2>
    <ul class="plain-list">
      ${listItems(story.boundaries)}
    </ul>
  </section>`;
}

function renderCutaways(storyBundle) {
  const cutaways = storyBundle.supporting_cutaways || [];
  if (!cutaways.length) return "";
  return `<section id="story-supporting-cutaways" class="panel span-12" data-panel="story-supporting-cutaways">
    <p class="section-kicker">Supporting cutaways</p>
    <h2>Other viewer-ready source stories</h2>
    <div class="record-grid two-col">
      ${cutaways.map((cutaway) => `<article class="fact-card">
        <span class="record-type">${esc(cutaway.role)}</span>
        <h3>${esc(cutaway.title)}</h3>
        <p>${esc(cutaway.summary)}</p>
        <div class="record-meta">
          <span>City: ${esc(cutaway.city)}</span>
          <span>Record IDs: ${esc((cutaway.source_record_ids || []).join(", "))}</span>
        </div>
        <p class="muted-copy">${esc(cutaway.limitation)}</p>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderTechnicalDrawer(storyBundle, scenarioLayer) {
  return `<section id="story-technical-drawer" class="panel span-12" data-panel="story-technical-drawer">
    <details id="technical-details">
      <summary>Show technical refs and raw packet ids</summary>
      <pre>${esc(JSON.stringify({ scenario_layer: scenarioLayer?.technical_refs || {}, story_bundle: storyBundle?.technical_refs || {} }, null, 2))}</pre>
    </details>
  </section>`;
}

export function renderStoryFirst(bundle) {
  const storyBundle = storyBundleFrom(bundle);
  const scenarioLayer = scenarioLayerFrom(bundle);
  const story = selectedStory(bundle);
  return [
    renderStoryHero(story),
    `<section id="story-beats" class="panel span-12" data-panel="story-beats">
      <p class="section-kicker">Story beats</p>
      <h2>What happened, in source-backed order</h2>
      <div class="story-beat-grid">${(story.beats || []).map(renderBeat).join("")}</div>
    </section>`,
    renderMapAnchor(story),
    renderEvidenceStack(story),
    renderConnection(story),
    renderHumanReview(story),
    renderCutaways(scenarioLayer || storyBundle),
    renderTechnicalDrawer(storyBundle, scenarioLayer)
  ].join("\n");
}
