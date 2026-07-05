const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function listItems(items, fallback = "None recorded.") {
  if (!items?.length) return `<li>${esc(fallback)}</li>`;
  return items.map((item) => `<li>${esc(item)}</li>`).join("");
}

function chipItems(items, fallback = "None recorded") {
  if (!items?.length) return `<span class="chip muted">${esc(fallback)}</span>`;
  return items.map((item) => `<span class="chip">${esc(item)}</span>`).join("");
}

function slug(value) {
  return String(value || "story").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function storyQueueFrom(bundle) {
  return bundle.storyQueue?.bundle || null;
}

export function hasStoryQueueBundle(bundle) {
  const queue = storyQueueFrom(bundle);
  return Boolean(queue?.primary_story_queue?.length >= 2 && queue?.status);
}

function queryKey(story) {
  return story.story_query_key || `${story.story_query_id || ""}@${story.query_version || ""}`;
}

function renderQueueCard(story, index) {
  const storySlug = slug(story.story_id || story.title || index);
  return `<article class="primary-story-card" data-role="primary_story" data-story-id="${esc(story.story_id)}" data-story-query-key="${esc(queryKey(story))}" data-city="${esc(story.city)}">
    <span class="record-type">${esc(story.city)} primary story</span>
    <h3>${esc(story.title)}</h3>
    <p class="story-card-place">${esc(story.specific_subject)}</p>
    <dl class="story-card-fields">
      <div><dt>Tension</dt><dd>${esc(story.tension)}</dd></div>
      <div><dt>Intelligence beat</dt><dd>${esc(story.intelligence_beat)}</dd></div>
      <div><dt>Review status</dt><dd>${esc(story.review_options_summary)}</dd></div>
      <div><dt>Boundary</dt><dd>${esc(story.boundary_summary)}</dd></div>
    </dl>
    <div class="story-card-actions">
      <a class="story-nav-link" href="#story-drilldown-${esc(storySlug)}">Open drilldown</a>
      <a class="story-nav-link secondary" href="#story-evidence-${esc(storySlug)}">Evidence</a>
      <a class="story-nav-link secondary" href="#story-options-${esc(storySlug)}">Options</a>
    </div>
  </article>`;
}

function renderQueueHero(queue) {
  const stories = queue.primary_story_queue || [];
  return `<section id="brain-surface-story-queue" class="hero-panel story-queue-hero span-12" data-panel="brain-surface-story-queue" data-brain-surface-default="story-queue">
    <div class="hero-copy">
      <p class="eyebrow">Situation queue</p>
      <h2>CityBrain story queue</h2>
      <p class="hero-line">Two validated, distinct review stories are shown first. Source records, technical refs, and cutaways sit inside each story instead of becoming the front page.</p>
      <div class="plain-status-row">
        <span class="status-pill safe">Primary stories: ${esc(stories.length)}</span>
        <span class="status-pill safe">Distinct story queries: ${esc(queue.distinct_story_query_count)}</span>
        <span class="status-pill safe">Queue-first baseline</span>
        <span class="status-pill">Human review required</span>
      </div>
    </div>
    <div class="hero-note">
      <strong>What this proves</strong>
      <p>${esc(queue.viewer_summary || "The maintained web surface can open on a story queue while preserving source, limitation, and no-action boundaries.")}</p>
    </div>
    <div class="story-card-grid">
      ${stories.map(renderQueueCard).join("")}
    </div>
  </section>`;
}

function renderSourceRecord(record) {
  return `<article class="mini-record source-ref-row" data-source-record-ref="${esc(record.source_record_id || record.source_id || record.id)}">
    <strong>${esc(record.title || record.source_record_id || record.source_id || "Source record")}</strong>
    <span>${esc(record.summary || record.source_dataset || record.record_role || "Source reference retained for review.")}</span>
  </article>`;
}

function renderWovenMoment(moment) {
  return `<article class="moment-card woven-moment-card" data-moment-role="${esc(moment.role)}">
    <span>${esc(moment.role_label || moment.role || "Woven moment")}</span>
    <h3>${esc(moment.title)}</h3>
    <p>${esc(moment.summary || moment.intelligence_beat || moment.boundary)}</p>
    <p class="muted-copy">${esc(moment.boundary || moment.viewer_readiness || "Review-only context.")}</p>
  </article>`;
}

function renderDrilldown(story) {
  const storySlug = slug(story.story_id || story.title);
  return `<section id="story-drilldown-${esc(storySlug)}" class="panel span-12 story-drilldown-panel" data-panel="story-drilldown" data-story-id="${esc(story.story_id)}" data-story-query-key="${esc(queryKey(story))}">
    <p class="section-kicker">${esc(story.city)} drilldown</p>
    <h2>${esc(story.title)}</h2>
    <div class="story-drilldown-grid">
      <section class="story-drilldown-block" id="story-situation-${esc(storySlug)}">
        <h3>What happened / review premise</h3>
        <p>${esc(story.review_premise || story.tension)}</p>
      </section>
      <section class="story-drilldown-block">
        <h3>What CityBrain connected</h3>
        <p>${esc(story.what_citybrain_connected || story.intelligence_beat)}</p>
      </section>
      <section class="story-drilldown-block">
        <h3>What is uncertain</h3>
        <ul class="plain-list compact">${listItems(story.uncertainty)}</ul>
      </section>
      <section class="story-drilldown-block boundary-block">
        <h3>Where it stops / human review boundary</h3>
        <p>${esc(story.human_stop)}</p>
      </section>
    </div>
    <div class="story-drilldown-grid two">
      <section class="story-drilldown-block" id="story-evidence-${esc(storySlug)}">
        <h3>Source records</h3>
        <div class="record-list">${(story.source_records || []).map(renderSourceRecord).join("")}</div>
      </section>
      <section class="story-drilldown-block" id="story-options-${esc(storySlug)}">
        <h3>Review-only choices</h3>
        <ul class="plain-list compact">${listItems(story.review_options)}</ul>
      </section>
    </div>
    <section class="story-drilldown-block" id="story-limitations-${esc(storySlug)}">
      <h3>Limitations</h3>
      <ul class="plain-list compact">${listItems(story.limitations)}</ul>
    </section>
    <section class="story-drilldown-block" id="story-woven-moments-${esc(storySlug)}">
      <h3>Cutaways and trust moments available</h3>
      <div class="moment-grid">${(story.woven_moments || []).map(renderWovenMoment).join("") || `<article class="moment-card"><span>Data depth note</span><h3>No woven moment rendered</h3><p>No validated cutaway or trust record was attached to this story.</p></article>`}</div>
    </section>
    <details class="story-technical-details">
      <summary>Show technical details / story query / source refs</summary>
      <pre>${esc(JSON.stringify({
        story_id: story.story_id,
        story_query_id: story.story_query_id,
        query_version: story.query_version,
        source_record_refs: story.source_record_refs,
        source_artifacts: story.source_artifacts,
        not_claimed: story.not_claimed
      }, null, 2))}</pre>
    </details>
  </section>`;
}

function renderDuplicateLedger(queue) {
  const duplicates = queue.duplicate_shape_not_counted || [];
  return `<section id="duplicate-shape-ledger" class="panel span-6" data-panel="duplicate-shape-ledger">
    <p class="section-kicker">Distinctness gate</p>
    <h2>Same-shape London examples stay parked</h2>
    <p class="human-explain">Only one proximity works/access story counts as a primary queue item. The remaining same-query examples are available as backlog context, not extra proof of breadth.</p>
    <div class="record-list">
      ${duplicates.map((item) => `<article class="mini-record"><strong>${esc(item.title)}</strong><span>${esc(item.reason)}</span></article>`).join("")}
    </div>
  </section>`;
}

function renderQueueBoundaries(queue) {
  return `<section id="brain-surface-boundaries" class="panel span-6" data-panel="brain-surface-boundaries">
    <p class="section-kicker">Boundary</p>
    <h2>Review context only</h2>
    <ul class="plain-list compact">${listItems(queue.global_boundaries)}</ul>
  </section>`;
}

export function renderStoryQueue(bundle) {
  const queue = storyQueueFrom(bundle);
  return [
    renderQueueHero(queue),
    ...(queue.primary_story_queue || []).map(renderDrilldown),
    renderDuplicateLedger(queue),
    renderQueueBoundaries(queue)
  ].join("\n");
}
