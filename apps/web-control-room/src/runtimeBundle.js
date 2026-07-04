import { loadAskV11HandoffFixtures } from "./askV11/askV11FixtureLoader.js";

export const BUNDLE_BASE = "/packages/fixtures/mobility_access/runtime_bundle/";
export const SOURCE_RECORD_BASE = "/packages/fixtures/mobility_access/source_record_bundle/";
export const SOURCE_RECORD_UI_BASE = "/packages/fixtures/source_record_ui_integrated/";
export const STORY_FIRST_BASE = "/packages/fixtures/story_first_demo/";
export const STORY_QUEUE_BASE = "/packages/fixtures/brain_surface_story_queue/";
export const PRODUCT_MODE_BASE = "/packages/fixtures/d9_product_modes/runtime_bundle/";
export const OPERATOR_COCKPIT_BASE = "/packages/fixtures/d9_operator_cockpit/runtime_overlay/";
export const OPERATOR_INTELLIGENCE_BASE = "/packages/fixtures/d10_operator_intelligence_depth/runtime_overlay/";
export const OPERATOR_WORKFLOW_BASE = "/packages/fixtures/d11_operator_workflow_review_workspace/runtime_overlay/";
export const D13_LIVE_SEAM_BASE = "/packages/fixtures/d13_live_web_kit_selection_receipt/runtime_overlay/";

async function readJsonFrom(base, name, optional = false) {
  const response = await fetch(base + name, { cache: "no-store" });
  if (optional && response.status === 404) return null;
  if (!response.ok) throw new Error(`Failed to load ${name}: ${response.status}`);
  return response.json();
}

async function readJson(name) {
  return readJsonFrom(BUNDLE_BASE, name);
}

async function readTrace() {
  const response = await fetch(BUNDLE_BASE + "trace.jsonl", { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to load trace.jsonl: ${response.status}`);
  const text = await response.text();
  return text.trim().split(/\n+/).filter(Boolean).map((line) => JSON.parse(line));
}

export async function loadRuntimeBundle() {
  const [oneTruth, scenario, review, evidence, options, trace, trackD, kitOverlay, labels, scoreboard, limitations, sourceRecordBundle, sourceRecordCards, sourceRecordGaps, sourceAttribution, integratedSourceBundle, integratedSourceIndex, integratedSourceBlockers, storyFirstBundle, storyScenarioLayer, storyQueueBundle, productModeBundle, operatorCockpitExtension, operatorIntelligenceExtension, operatorWorkflowExtension, d13LiveSelectionEvent, askV11HandoffFixtures] = await Promise.all([
    readJson("one_truth_index.json"),
    readJson("scenario_state.json"),
    readJson("review_state.json"),
    readJson("evidence_bundle.json"),
    readJson("option_sets.json"),
    readTrace(),
    readJson("track_d_packets.json"),
    readJson("kit_overlay_packets.json"),
    readJson("claim_labels.json"),
    readJson("moment_scoreboard.json"),
    readJson("limitations.json"),
    readJsonFrom(SOURCE_RECORD_BASE, "source_record_bundle.json", true),
    readJsonFrom(SOURCE_RECORD_BASE, "source_record_cards.json", true),
    readJsonFrom(SOURCE_RECORD_BASE, "source_record_gaps.json", true),
    readJsonFrom(SOURCE_RECORD_BASE, "source_attribution_ledger.json", true),
    readJsonFrom(SOURCE_RECORD_UI_BASE, "source_record_ui_integrated_bundle.json", true),
    readJsonFrom(SOURCE_RECORD_UI_BASE, "source_record_ui_card_index.json", true),
    readJsonFrom(SOURCE_RECORD_UI_BASE, "source_record_ui_data_depth_blockers.json", true),
    readJsonFrom(STORY_FIRST_BASE, "story_source_bundle.json", true),
    readJsonFrom(STORY_FIRST_BASE, "story_scenario_layer.json", true),
    readJsonFrom(STORY_QUEUE_BASE, "brain_surface_story_queue_bundle.json", true),
    readJsonFrom(PRODUCT_MODE_BASE, "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json", true),
    readJsonFrom(OPERATOR_COCKPIT_BASE, "D9_OPERATOR_COCKPIT_RUNTIME_EXTENSION.json", true),
    readJsonFrom(OPERATOR_INTELLIGENCE_BASE, "D10_OPERATOR_INTELLIGENCE_DEPTH_EXTENSION.json", true),
    readJsonFrom(OPERATOR_WORKFLOW_BASE, "D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json", true),
    readJsonFrom(D13_LIVE_SEAM_BASE, "D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json", true),
    loadAskV11HandoffFixtures(readJsonFrom)
  ]);
  return {
    oneTruth,
    scenario,
    review,
    evidence,
    options,
    trace,
    trackD,
    kitOverlay,
    labels,
    scoreboard,
    limitations,
    sourceRecords: {
      bundle: sourceRecordBundle,
      cards: sourceRecordCards,
      gaps: sourceRecordGaps,
      attribution: sourceAttribution
    },
    integratedSourceRecords: {
      bundle: integratedSourceBundle,
      index: integratedSourceIndex,
      blockers: integratedSourceBlockers
    },
    storyFirst: {
      bundle: storyFirstBundle,
      scenarioLayer: storyScenarioLayer
    },
    storyQueue: {
      bundle: storyQueueBundle
    },
    productModes: {
      bundle: productModeBundle
    },
    operatorCockpit: {
      runtimeExtension: operatorCockpitExtension,
      intelligenceExtension: operatorIntelligenceExtension,
      workflowExtension: operatorWorkflowExtension
    },
    spatialSeam: {
      liveSelectionEvent: d13LiveSelectionEvent
    },
    askV11: {
      handoffFixtures: askV11HandoffFixtures
    }
  };
}
