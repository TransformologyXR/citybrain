export const ASK_V11_HANDOFF_BASE = "/outputs/ask_v11_app_handoff_preflight/";
export const ASK_V11_HANDOFF_FIXTURE_FILE = "ASK_V11_APP_HANDOFF_FIXTURES.json";

export async function loadAskV11HandoffFixtures(readJsonFrom) {
  return readJsonFrom(ASK_V11_HANDOFF_BASE, ASK_V11_HANDOFF_FIXTURE_FILE, true);
}
