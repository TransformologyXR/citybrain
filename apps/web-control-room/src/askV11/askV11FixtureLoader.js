export const ASK_V11_HANDOFF_BASE = "/apps/web-control-room/src/askV11/fixtures/";
export const ASK_V11_HANDOFF_FIXTURE_FILE = "askV11AppHandoffFixtures.json";
export const ASK_V11_HANDOFF_LEGACY_BASE = "/outputs/ask_v11_app_handoff_preflight/";
export const ASK_V11_HANDOFF_LEGACY_FIXTURE_FILE = "ASK_V11_APP_HANDOFF_FIXTURES.json";

export async function loadAskV11HandoffFixtures(readJsonFrom, options = {}) {
  const base = options.base || ASK_V11_HANDOFF_BASE;
  const file = options.file || ASK_V11_HANDOFF_FIXTURE_FILE;
  const fixtureSet = await readJsonFrom(base, file, true);
  if (fixtureSet || options.disableLegacyFallback) return fixtureSet;
  return readJsonFrom(
    options.legacyBase || ASK_V11_HANDOFF_LEGACY_BASE,
    options.legacyFile || ASK_V11_HANDOFF_LEGACY_FIXTURE_FILE,
    true
  );
}
