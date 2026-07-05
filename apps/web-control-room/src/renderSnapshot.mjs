import fs from "node:fs";
import path from "node:path";
import { renderApp } from "./renderApp.js";

const repoRoot = process.cwd();
const bundleRoot = path.join(repoRoot, "packages", "fixtures", "mobility_access", "runtime_bundle");
const sourceRecordRoot = path.join(repoRoot, "packages", "fixtures", "mobility_access", "source_record_bundle");
const integratedSourceRecordRoot = path.join(repoRoot, "packages", "fixtures", "source_record_ui_integrated");
const storyFirstRoot = path.join(repoRoot, "packages", "fixtures", "story_first_demo");
const storyQueueRoot = path.join(repoRoot, "packages", "fixtures", "brain_surface_story_queue");
const productModeRoot = path.join(repoRoot, "packages", "fixtures", "d9_product_modes", "runtime_bundle");
const operatorCockpitRoot = path.join(repoRoot, "packages", "fixtures", "d9_operator_cockpit", "runtime_overlay");
const operatorIntelligenceRoot = path.join(repoRoot, "packages", "fixtures", "d10_operator_intelligence_depth", "runtime_overlay");
const operatorWorkflowRoot = path.join(repoRoot, "packages", "fixtures", "d11_operator_workflow_review_workspace", "runtime_overlay");
const d13LiveSeamRoot = path.join(repoRoot, "packages", "fixtures", "d13_live_web_kit_selection_receipt", "runtime_overlay");
const output = process.argv[2] || path.join(repoRoot, "tmp", "WEB_LAUNCH_DOM_CAPTURE.html");

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(bundleRoot, name), "utf8"));
}

function readOptionalSourceJson(name) {
  const target = path.join(sourceRecordRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalIntegratedJson(name) {
  const target = path.join(integratedSourceRecordRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalStoryJson(name) {
  const target = path.join(storyFirstRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalStoryQueueJson(name) {
  const target = path.join(storyQueueRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalProductModeJson(name) {
  const target = path.join(productModeRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalOperatorCockpitJson(name) {
  const target = path.join(operatorCockpitRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalOperatorIntelligenceJson(name) {
  const target = path.join(operatorIntelligenceRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalOperatorWorkflowJson(name) {
  const target = path.join(operatorWorkflowRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readOptionalD13LiveSeamJson(name) {
  const target = path.join(d13LiveSeamRoot, name);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8"));
}

function readTrace() {
  return fs.readFileSync(path.join(bundleRoot, "trace.jsonl"), "utf8")
    .trim()
    .split(/\n+/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

const bundle = {
  oneTruth: readJson("one_truth_index.json"),
  scenario: readJson("scenario_state.json"),
  review: readJson("review_state.json"),
  evidence: readJson("evidence_bundle.json"),
  options: readJson("option_sets.json"),
  trace: readTrace(),
  trackD: readJson("track_d_packets.json"),
  kitOverlay: readJson("kit_overlay_packets.json"),
  labels: readJson("claim_labels.json"),
  scoreboard: readJson("moment_scoreboard.json"),
  limitations: readJson("limitations.json"),
  sourceRecords: {
    bundle: readOptionalSourceJson("source_record_bundle.json"),
    cards: readOptionalSourceJson("source_record_cards.json"),
    gaps: readOptionalSourceJson("source_record_gaps.json"),
    attribution: readOptionalSourceJson("source_attribution_ledger.json")
  },
  integratedSourceRecords: {
    bundle: readOptionalIntegratedJson("source_record_ui_integrated_bundle.json"),
    index: readOptionalIntegratedJson("source_record_ui_card_index.json"),
    blockers: readOptionalIntegratedJson("source_record_ui_data_depth_blockers.json")
  },
  storyFirst: {
    bundle: readOptionalStoryJson("story_source_bundle.json"),
    scenarioLayer: readOptionalStoryJson("story_scenario_layer.json")
  },
  storyQueue: {
    bundle: readOptionalStoryQueueJson("brain_surface_story_queue_bundle.json")
  },
  productModes: {
    bundle: readOptionalProductModeJson("D9_PRODUCT_MODE_RUNTIME_BUNDLE.json")
  },
  operatorCockpit: {
    runtimeExtension: readOptionalOperatorCockpitJson("D9_OPERATOR_COCKPIT_RUNTIME_EXTENSION.json"),
    intelligenceExtension: readOptionalOperatorIntelligenceJson("D10_OPERATOR_INTELLIGENCE_DEPTH_EXTENSION.json"),
    workflowExtension: readOptionalOperatorWorkflowJson("D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json")
  },
  spatialSeam: {
    liveSelectionEvent: readOptionalD13LiveSeamJson("D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json")
  }
};

const html = `<!doctype html><html><body data-source-record-status="${bundle.productModes.bundle?.status || bundle.storyQueue.bundle?.status || bundle.storyFirst.scenarioLayer?.status || bundle.storyFirst.bundle?.status || bundle.integratedSourceRecords.bundle?.status || bundle.sourceRecords.bundle?.status || "missing"}" data-execution-state="${bundle.productModes.bundle?.execution_state || bundle.oneTruth.execution_state}">${renderApp(bundle)}</body></html>`;
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, html, "utf8");
console.log(output);
