import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text())


def test_expected_core_files_exist():
    required = [
        'README.md','CODEX_TASK_PROMPT.md','IMPLEMENTATION_PLAN.md','ACCEPTANCE_CRITERIA.md','NON_GOALS_AND_BOUNDARIES.md',
        'artifacts_to_add/templates/E3_PUBLICATION_HOME_SWEEP_REPORT.template.json',
        'artifacts_to_add/templates/E3_MASTER_LEDGER.template.json',
        'artifacts_to_add/templates/E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.template.json',
        'artifacts_to_add/templates/E3_FORECAST_RESULT_FRAMING_ROW.template.json',
        'artifacts_to_add/templates/E3_CITY_DIVERGENCE_WARNING_ROW.template.json',
        'artifacts_to_add/templates/E3_ARMING_HANDOFF_TO_EPOCH4.template.json'
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_learned_registry_snapshot_only_allows_one_experimental_component():
    snap = load('artifacts_to_add/templates/E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.template.json')
    comps = snap['allowed_experimental_components']
    assert len(comps) == 1
    c = comps[0]
    assert c['component_id'] == 'forecast.permit_stall_v0.r1'
    assert c['status'] == 'experimental'
    assert c['consuming_surfaces'] == []
    assert c['frozen_replay_only'] is True
    assert c['release_ledger_row'] is None


def test_forecast_framing_states_pipeline_validated_not_deployable():
    row = load('artifacts_to_add/templates/E3_FORECAST_RESULT_FRAMING_ROW.template.json')
    assert row['headline'] == 'pipeline_validated_model_not_deployable'
    assert row['product_surface_armed'] is False
    assert row['operator_facing_forecast_armed'] is False
    assert row['average_precision']['model'] > row['average_precision']['baseline_proxy']


def test_epoch4_handoff_inherits_thresholds():
    handoff = load('artifacts_to_add/templates/E3_ARMING_HANDOFF_TO_EPOCH4.template.json')
    assert 'arming_status_evaluator' in handoff['inherited_infrastructure']
    assert handoff['thresholds_relitigated_in_epoch4'] is False
    assert handoff['governance_delta_required_to_change_thresholds'] is True


def test_no_forbidden_capability_audit_is_strict():
    audit = load('artifacts_to_add/templates/E3_NO_FORBIDDEN_CAPABILITY_AUDIT.template.json')
    assert audit['status'] == 'PASS'
    assert audit['new_learned_registry_entries'] == 0
    forbidden = [k for k in audit if k.endswith('_created')]
    assert forbidden
    for k in forbidden:
        assert audit[k] is False
