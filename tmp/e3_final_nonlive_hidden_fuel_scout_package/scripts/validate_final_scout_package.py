from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "CODEX_TASK_PROMPT.md",
    "IMPLEMENTATION_PLAN.md",
    "ACCEPTANCE_CRITERIA.md",
    "NON_GOALS_AND_BOUNDARIES.md",
    "schemas/final_scout_decision.schema.json",
    "schemas/backlog_item.schema.json",
    "artifacts_to_add/templates/E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.template.json",
    "artifacts_to_add/templates/E3_PUBLICATION_HOME_RECOMMENDATION_ROW.template.json",
]

def main():
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {missing}")
    decision = json.loads((ROOT / "artifacts_to_add/templates/E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.template.json").read_text())
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1"
    assert decision["promotion_status"] == "candidate_inventory_and_backlog_only"
    assert decision["non_live_assumption"] is True
    print("PASS_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_PACKAGE_SELF_CHECK")

if __name__ == "__main__":
    main()
