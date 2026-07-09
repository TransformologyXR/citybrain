from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]

required = [
    "README.md",
    "CODEX_TASK_PROMPT.md",
    "IMPLEMENTATION_PLAN.md",
    "ACCEPTANCE_CRITERIA.md",
    "NON_GOALS_AND_BOUNDARIES.md",
    "manifests/scout_lane_manifest.json",
    "manifests/artifact_root_search_manifest.json",
    "manifests/hidden_fuel_signal_taxonomy.json",
    "artifacts_to_add/templates/E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.template.json",
]

def main():
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing:
        print("MISSING", missing)
        return 1
    for p in ROOT.rglob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"BAD_JSON {p}: {e}")
            return 1
    print("PASS_HIDDEN_DATA_SCOUT_CODEX_PACKAGE_SELF_CHECK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
