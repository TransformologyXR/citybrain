import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "outputs" / "ask_v11_app_handoff_preflight" / "ASK_V11_APP_HANDOFF_FIXTURES.json"
VIEW_PATH = ROOT / "apps" / "web-control-room" / "src" / "views" / "askV11Handoff.js"
ADAPTER_PATH = ROOT / "apps" / "web-control-room" / "src" / "askV11" / "askV11HandoffAdapter.js"
LOADER_PATH = ROOT / "apps" / "web-control-room" / "src" / "askV11" / "askV11FixtureLoader.js"
RUNTIME_BUNDLE_PATH = ROOT / "apps" / "web-control-room" / "src" / "runtimeBundle.js"


def load_fixture_set():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def render_fixture_html():
    script = textwrap.dedent(
        f"""
        import fs from "node:fs";
        import {{ renderAskV11Handoff }} from {json.dumps(VIEW_PATH.as_uri())};
        const fixtureSet = JSON.parse(fs.readFileSync({json.dumps(str(FIXTURE_PATH))}, "utf8"));
        process.stdout.write(renderAskV11Handoff({{ askV11: {{ handoffFixtures: fixtureSet }} }}));
        """
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout


class AskV11AppHandoffR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_set = load_fixture_set()
        cls.html = render_fixture_html()

    def scenario_html(self, scenario_id):
        marker = f'data-ask-v11-scenario="{scenario_id}"'
        start = self.html.index(marker)
        next_start = self.html.find('data-ask-v11-scenario="', start + len(marker))
        return self.html[start: next_start if next_start != -1 else len(self.html)]

    def test_fixture_selector_loader_works_locally(self):
        scenarios = [fixture["scenario_id"] for fixture in self.fixture_set["fixtures"]]
        self.assertEqual(8, len(scenarios))
        for scenario in scenarios:
            self.assertIn(f'data-ask-v11-scenario-link="{scenario}"', self.html)
        loader_source = LOADER_PATH.read_text(encoding="utf-8")
        self.assertIn("/outputs/ask_v11_app_handoff_preflight/", loader_source)

    def test_cannot_claim_visible_when_present(self):
        self.assertIn('data-ui-section="cannot_claim"', self.html)
        self.assertIn("No official external action was executed.", self.html)

    def test_no_data_visible_when_present(self):
        no_data = self.scenario_html("no_data_answer")
        self.assertIn('data-ask-v11-no-data="true"', no_data)
        self.assertIn("No retained facts, rows, or series were found", no_data)

    def test_not_executed_visible_when_present(self):
        external = self.scenario_html("external_context_cannot_claim")
        self.assertIn('data-ui-section="not_executed"', external)
        self.assertIn("live_external_source:charger_asset_availability", external)
        self.assertIn("production_retrieval", external)

    def test_check_details_visible(self):
        self.assertIn('data-ui-section="check_details"', self.html)
        self.assertIn("Claimability:", self.html)
        self.assertIn('data-ui-section="downgrade"', self.html)

    def test_citations_and_source_refs_visible(self):
        self.assertIn('data-ui-section="citations"', self.html)
        self.assertIn('data-ui-section="citation"', self.html)
        self.assertIn('data-ui-section="source_ref"', self.html)

    def test_trace_visible(self):
        self.assertIn('data-ui-section="trace"', self.html)
        self.assertIn('data-ui-section="trace_hop"', self.html)
        self.assertIn("boundary_screen@1.1", self.html)

    def test_clarification_visible(self):
        clarification = self.scenario_html("clarification_required")
        self.assertIn('data-ui-section="clarification"', clarification)
        self.assertIn("Which asset, place, source record, or selected item should I use?", clarification)
        self.assertNotIn('data-ui-section="check_details"', clarification)

    def test_boundary_action_refusal_visible(self):
        refusal = self.scenario_html("boundary_action_refusal")
        self.assertIn('data-ui-section="boundary_refusal"', refusal)
        self.assertIn("action_shaped", refusal)
        self.assertIn("G5", refusal)

    def test_degraded_render_visible(self):
        degraded = self.scenario_html("render_validator_degraded")
        self.assertIn('data-ask-v11-degraded="true"', degraded)
        self.assertIn('data-ui-section="degraded_render"', degraded)
        self.assertIn("render attempts to un-downgrade proximity claim", degraded)

    def test_proximity_case_does_not_display_unsupported_causal_claim_as_known(self):
        proximity = self.scenario_html("proximity_not_causality")
        knowns_start = proximity.index('data-ui-section="knowns"')
        knowns_end = proximity.index('data-ui-section="unknowns"')
        knowns = proximity[knowns_start:knowns_end].lower()
        self.assertNotIn("blocked", knowns)
        self.assertNotIn("caused", knowns)
        self.assertNotIn("confirmed impact", knowns)
        self.assertIn('data-ui-section="cannot_claim"', proximity)

    def test_external_context_does_not_display_live_availability_as_fact(self):
        external = self.scenario_html("external_context_cannot_claim")
        knowns_start = external.index('data-ui-section="knowns"')
        knowns_end = external.index('data-ui-section="unknowns"')
        knowns = external[knowns_start:knowns_end].lower()
        self.assertNotIn("current charger availability", knowns)
        self.assertNotIn("live occupancy", knowns)
        self.assertIn('data-ui-section="cannot_claim"', external)

    def test_no_action_ticket_dispatch_enforcement_affordance_appears(self):
        ask_panel_start = self.html.index('data-ask-v11-handoff="true"')
        ask_html = self.html[ask_panel_start:]
        self.assertNotIn("<button", ask_html.lower())
        self.assertNotIn('data-review-verb', ask_html)
        self.assertNotIn('data-command="dispatch"', ask_html)
        self.assertNotIn('data-command="create_case"', ask_html)
        self.assertNotIn('data-command="create_ticket"', ask_html)
        self.assertNotIn('data-command="enforce"', ask_html)

    def test_app_adapter_does_not_fetch_citation_urls(self):
        adapter_source = ADAPTER_PATH.read_text(encoding="utf-8")
        view_source = VIEW_PATH.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", adapter_source)
        self.assertNotIn("fetch(", view_source)
        self.assertNotIn("http://", adapter_source + view_source)
        self.assertNotIn("https://", adapter_source + view_source)

    def test_app_adapter_does_not_invoke_ask_runtime_or_llm(self):
        changed_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [ADAPTER_PATH, VIEW_PATH, LOADER_PATH, RUNTIME_BUNDLE_PATH]
        )
        self.assertNotIn("packages/ask_v11", changed_sources)
        self.assertNotIn("openai", changed_sources.lower())
        self.assertNotIn("llm", changed_sources.lower())
        self.assertNotIn("chat.completions", changed_sources.lower())

    def test_fixture_payloads_have_no_raw_query_key(self):
        adapter_source = ADAPTER_PATH.read_text(encoding="utf-8")
        self.assertIn("hasRawQueryKey", adapter_source)
        serialized = json.dumps(self.fixture_set)
        self.assertNotIn('"raw_query"', serialized)


if __name__ == "__main__":
    unittest.main()
