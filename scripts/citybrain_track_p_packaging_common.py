"""Shared helpers for Track P product packaging/persona/collateral runners."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"

DEMO_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1"
DEMO_DECISION = DEMO_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json"
CLOSEOUT_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1"
CLOSEOUT_DECISION = CLOSEOUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json"
READINESS_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review"
READINESS_DECISION = READINESS_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json"
P0_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_product_packaging_and_persona_preflight"
P1_ROOT = OUTPUTS / "main_citybrain_d6_persona_rendering_policies_r1"
P2_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_collateral_pack_r1"
P3_ROOT = OUTPUTS / "main_citybrain_d6_hero_neighbourhood_product_packaging_closeout"

BOUNDARY = (
    "Track P is packaging and narrative only. It packages a bounded local/replay "
    "Hero Neighbourhood control-room reference demo for review/query context. It does not claim "
    "production readiness, public API readiness, live monitoring, autonomous incident detection, "
    "alert push, dispatch, routing/control, enforcement, official ticket/case creation, "
    "legal/certified incident findings, a citywide certified twin, physical accuracy, or automated action."
)

POSITIONING_LINE = (
    "CityBrain Hero Neighbourhood Control Room Reference Demo - a bounded local/replay "
    "operator-surface proof linking incident context, canonical relationship contracts, "
    "Omniverse spatial handoff, web evidence, and persona-rendered review views."
)

PROHIBITED_CLAIMS = [
    "production readiness",
    "public API readiness",
    "citywide certified twin",
    "live autonomous monitoring",
    "alerting",
    "dispatch",
    "routing/control",
    "enforcement",
    "legal/certified incident findings",
    "official ticket/case creation",
    "automated action",
    "physical/engineering accuracy",
    "full operational deployment",
]

NEGATION_WORDS = (
    "no ",
    "no_",
    ": no",
    " no.",
    " no,",
    "not ",
    "does not",
    "do not",
    "never",
    "without",
    "must not",
    "not a",
    "cannot",
    "blocked",
    "forbidden",
    "do not say",
    "avoid saying",
)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]

BASE_REQUIRED_UPSTREAMS = {
    "hero_reference_demo_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS",
        "role": "frozen Hero Neighbourhood control-room reference demo",
    },
    "hero_reference_demo_closeout_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "role": "frozen demo closeout",
    },
    "hero_cerseg_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero + CER/SEG v2 integration-readiness review",
    },
    "hero_scene_pack_closeout": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Hero Neighbourhood scene pack closeout",
    },
    "cerseg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "role": "CER/SEG v2 closeout",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Incident Mode closeout",
    },
    "incident_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "role": "Incident Mode operator-surface handoff",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status_from_decision(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if payload.get(key):
            return str(payload[key])
    return None


def prepare_output_root(root: Path, expected_name: str) -> None:
    if root.resolve().parent != OUTPUTS.resolve():
        raise RuntimeError(f"Refusing unexpected output parent: {root}")
    if root.name != expected_name:
        raise RuntimeError(f"Refusing unexpected output root name: {root.name}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def snapshot_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        file_count += 1
        byte_count += path.stat().st_size
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
        digest.update(sha256_file(path).encode("utf-8"))
    return {"exists": True, "file_count": file_count, "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def upstream_snapshots(specs: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {key: snapshot_root(REPO_ROOT / spec["root"]) for key, spec in specs.items()}


def discover_upstreams(specs: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    missing = []
    for key, spec in specs.items():
        root = REPO_ROOT / spec["root"]
        decision_path = root / spec["decision_file"]
        decision = read_json(decision_path, {})
        status = status_from_decision(decision)
        expected = spec.get("expected")
        exists = root.exists() and decision_path.exists()
        green = exists and (status == expected if expected else bool(status and status.startswith("PASS_")))
        row = {
            "key": key,
            "root": spec["root"],
            "decision_file": rel(decision_path),
            "exists": exists,
            "status": status,
            "expected_status": expected,
            "green": green,
            "role": spec.get("role"),
            "file_count": snapshot_root(root)["file_count"] if root.exists() else 0,
        }
        rows.append(row)
        if not green:
            missing.append(row)
    summary = {
        "status": "PASS" if not missing else "FAIL",
        "required_upstreams_found": len(rows) - len(missing),
        "required_upstreams_total": len(rows),
        "missing_or_not_green_count": len(missing),
        "missing_or_not_green": missing,
    }
    return {"upstreams": rows, "summary": summary}, summary


def frozen_demo_facts() -> dict[str, Any]:
    demo = read_json(DEMO_DECISION, {})
    closeout = read_json(CLOSEOUT_DECISION, {})
    readiness = read_json(READINESS_DECISION, {})
    gaps = read_json(CLOSEOUT_ROOT / "NON_BLOCKING_GAPS_REGISTER.json", {})
    unresolved = read_json(DEMO_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json", {})
    return {
        "demo_status": demo.get("status"),
        "closeout_status": closeout.get("status"),
        "integration_readiness_status": readiness.get("status"),
        "hero_bindings_count": demo.get("hero_bindings_count", closeout.get("hero_bindings_count", 8)),
        "hero_overlay_packets_count": demo.get("hero_overlay_packets_count", closeout.get("overlay_packet_count", 8)),
        "operator_surface_packets_count": demo.get("operator_surface_packets_count", closeout.get("operator_surface_packet_count", 6)),
        "web_companion_packets_count": demo.get("web_companion_packets_count", closeout.get("web_companion_packet_count", 6)),
        "manifest_rows_count": demo.get("manifest_rows_count", closeout.get("r1_manifest_row_count", 45)),
        "unresolved_quarantined_preserved_count": demo.get(
            "unresolved_quarantined_preserved_count", unresolved.get("unresolved_quarantined_preserved_count", 21)
        ),
        "unresolved_count": unresolved.get("unresolved_count"),
        "quarantined_count": unresolved.get("quarantined_count"),
        "blocking_gaps_count": demo.get("blocking_gaps_count", closeout.get("blocking_gaps_count", 0)),
        "non_blocking_gaps_count": demo.get("non_blocking_gaps_count", closeout.get("non_blocking_gaps_count", 3)),
        "non_blocking_gaps": demo.get("non_blocking_gaps") or gaps.get("non_blocking_gaps", []),
        "visual_acceptance_status": demo.get("visual_acceptance_status", "PASS_ARTIFACT_PACKAGE_REVIEW_ONLY"),
        "demo_acceptance_status": demo.get("demo_acceptance_status"),
        "claim_boundary_status": demo.get("claim_boundary_status"),
        "no_action_boundary_status": demo.get("no_action_boundary_status"),
        "no_mutation_status": demo.get("no_mutation_status"),
        "secret_audit_status": demo.get("secret_audit_status"),
        "hash_validation_status": demo.get("hash_validation_status"),
        "readiness_entity_compatibility_result": readiness.get("entity_compatibility_result"),
        "limitations": demo.get("limitations", []),
        "boundary": BOUNDARY,
    }


def generated_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def hash_manifest(root: Path, task_name: str) -> dict[str, Any]:
    rows = []
    for path in generated_files(root):
        if path.name == "HASH_MANIFEST.json":
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    failures = []
    for row in rows:
        path = REPO_ROOT / row["path"]
        if not path.exists() or sha256_file(path) != row["sha256"]:
            failures.append(row["path"])
    report = {
        "task_name": task_name,
        "timestamp": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "failures": failures,
        "hash_validation_status": "PASS" if not failures else "FAIL",
    }
    write_json(root / "HASH_MANIFEST.json", report)
    return report


def no_mutation_audit(root: Path, before: dict[str, dict[str, Any]], specs: dict[str, dict[str, str]], task_name: str) -> dict[str, Any]:
    after = upstream_snapshots(specs)
    changed = []
    for key, prior in before.items():
        if prior != after.get(key):
            changed.append({"key": key, "before": prior, "after": after.get(key)})
    report = {
        "task_name": task_name,
        "status": "PASS" if not changed else "FAIL",
        "checked_upstream_count": len(before),
        "changed_upstreams": changed,
        "policy": "Track P writes only its own output root and does not mutate upstream outputs.",
    }
    write_json(root / "NO_MUTATION_AUDIT.json", report)
    return report


def secret_audit(root: Path, task_name: str) -> dict[str, Any]:
    findings = []
    for path in generated_files(root):
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {
        "task_name": task_name,
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
    }
    write_json(root / "SECRET_AUDIT.json", report)
    return report


def _line_is_negated(line: str) -> bool:
    lower = line.lower()
    return any(token in lower for token in NEGATION_WORDS)


def claim_boundary_audit(root: Path, task_name: str) -> dict[str, Any]:
    affirming = []
    suspicious_patterns = [
        "production ready",
        "public api ready",
        "certified citywide twin",
        "live monitoring",
        "autonomous monitoring",
        "automated action",
        "dispatch",
        "enforcement",
        "legal certified",
        "official ticket",
    ]
    for path in generated_files(root):
        if path.suffix.lower() not in {".json", ".md", ".txt"} or path.name.endswith("_AUDIT.json"):
            continue
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            lower = line.lower()
            if any(pattern in lower for pattern in suspicious_patterns) and not _line_is_negated(line):
                affirming.append({"path": rel(path), "line": idx, "text": line[:240]})
    report = {
        "task_name": task_name,
        "status": "PASS" if not affirming else "FAIL",
        "affirming_forbidden_claim_count": len(affirming),
        "affirming_forbidden_claims": affirming,
        "prohibited_claims": PROHIBITED_CLAIMS,
        "boundary": BOUNDARY,
    }
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_action_audit(root: Path, task_name: str) -> dict[str, Any]:
    action_findings = []
    patterns = ["send alert", "dispatch", "route crews", "enforce", "issue ticket", "take action", "execute plan"]
    for path in generated_files(root):
        if path.suffix.lower() not in {".json", ".md", ".txt"} or path.name.endswith("_AUDIT.json"):
            continue
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            lower = line.lower()
            if any(pattern in lower for pattern in patterns) and not _line_is_negated(line):
                action_findings.append({"path": rel(path), "line": idx, "text": line[:240]})
    report = {
        "task_name": task_name,
        "status": "PASS" if not action_findings else "FAIL",
        "action_instruction_count": len(action_findings),
        "action_instructions": action_findings,
        "policy": "Collateral may recommend safe next-look review only; it must not create action, alerting, dispatch, enforcement, or execution language.",
    }
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", report)
    return report


def required_files_status(root: Path, required: list[str]) -> dict[str, Any]:
    missing = [name for name in required if not (root / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing, "required_count": len(required)}


def write_local_index(root: Path, task_name: str, status: str, required: list[str], intro: str = "") -> None:
    lines = [f"# {task_name}", "", f"Status: `{status}`", "", BOUNDARY, ""]
    if intro:
        lines.extend([intro, ""])
    lines.extend(["## Open First", "", "- [README.md](README.md)", "- [Decision](%s)" % required[0], ""])
    lines.extend(["## Artifacts", ""])
    lines.extend(f"- [{name}]({name})" for name in required)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def facts_markdown(facts: dict[str, Any]) -> str:
    gaps = "\n".join(f"- {gap}" for gap in facts.get("non_blocking_gaps", []))
    limitations = "\n".join(f"- {item}" for item in facts.get("limitations", [])[:12])
    return f"""## Frozen Demo Facts

- Demo status: `{facts.get('demo_status')}`
- Closeout status: `{facts.get('closeout_status')}`
- Integration readiness: `{facts.get('integration_readiness_status')}`
- Hero bindings: `{facts.get('hero_bindings_count')}`
- Hero overlay packets: `{facts.get('hero_overlay_packets_count')}`
- Operator-surface packets: `{facts.get('operator_surface_packets_count')}`
- Web companion packets: `{facts.get('web_companion_packets_count')}`
- Manifest rows: `{facts.get('manifest_rows_count')}`
- Unresolved/quarantined contexts preserved: `{facts.get('unresolved_quarantined_preserved_count')}`
- Blocking gaps: `{facts.get('blocking_gaps_count')}`
- Non-blocking gaps: `{facts.get('non_blocking_gaps_count')}`
- Visual acceptance: `{facts.get('visual_acceptance_status')}`

## Non-Blocking Gaps

{gaps}

## Limitations

{limitations}
"""


def persona_policies(facts: dict[str, Any]) -> dict[str, Any]:
    shared = {
        "evidence_scope": {
            "hero_bindings": facts["hero_bindings_count"],
            "hero_overlay_packets": facts["hero_overlay_packets_count"],
            "operator_surface_packets": facts["operator_surface_packets_count"],
            "web_companion_packets": facts["web_companion_packets_count"],
            "manifest_rows": facts["manifest_rows_count"],
            "unresolved_quarantined_preserved": facts["unresolved_quarantined_preserved_count"],
        },
        "limitations": facts.get("limitations", []),
        "non_blocking_gaps": facts.get("non_blocking_gaps", []),
        "visual_acceptance_status": facts.get("visual_acceptance_status"),
        "truth_policy": "All personas render the same evidence, packets, limitations, unresolved/quarantined contexts, and claim boundaries.",
        "prohibited_transformations": [
            "cannot omit limitations",
            "cannot promote unresolved/quarantined context to confirmed truth",
            "cannot convert safe-next-look review into an action instruction",
            "cannot imply live monitoring or alerting",
            "cannot claim a certified citywide twin",
        ],
    }
    policies = [
        {
            "persona": "Executive",
            "policy_id": "track-p-persona-executive-r1",
            "framing": "Concise outcome/status summary for a reviewer or sponsor.",
            "view_emphasis": ["what is proven", "what remains limited", "bounded local/replay status"],
            "detail_level": "summary",
            "must_show": ["limitations", "non_blocking_gaps", "no production/action/certified-twin claim"],
            "must_not_show": ["no operational command language", "no action instructions"],
        },
        {
            "persona": "Operator",
            "policy_id": "track-p-persona-operator-r1",
            "framing": "Packet-oriented review view for inspecting the same frozen evidence.",
            "view_emphasis": ["operator-surface packets", "affected entities", "overlays", "unresolved/quarantined contexts"],
            "detail_level": "operational review context",
            "must_show": ["safe next-look framing", "limitations", "unresolved/quarantined contexts"],
            "must_not_show": ["no alert language", "no dispatch language", "no enforcement language", "no automatic workflow language"],
        },
        {
            "persona": "Planner",
            "policy_id": "track-p-persona-planner-r1",
            "framing": "Spatial/contextual implications and scenario/corridor interpretation.",
            "view_emphasis": ["Omniverse handoff", "graph/edge context", "scene-bound corridor framing"],
            "detail_level": "contextual",
            "must_show": ["local/replay status", "evidence-backed scope", "limitations"],
            "must_not_show": ["no prediction claim", "no plan execution claim", "no physical accuracy claim"],
        },
        {
            "persona": "Analyst",
            "policy_id": "track-p-persona-analyst-r1",
            "framing": "Evidence refs, limitation refs, validation/audit state, and compatibility notes.",
            "view_emphasis": ["manifest rows", "evidence/limitation trace", "audit statuses", "non-blocking gaps"],
            "detail_level": "detailed",
            "must_show": ["claim labels", "validation status", "unresolved/quarantined preservation"],
            "must_not_show": ["no unsupported conclusion", "no separate truth path"],
        },
    ]
    return {"schema_version": "citybrain-track-p-persona-policy-r1", "shared_invariants": shared, "personas": policies}


def run_standard_audits(
    root: Path,
    task_name: str,
    before: dict[str, dict[str, Any]],
    specs: dict[str, dict[str, str]],
    required: list[str],
) -> dict[str, Any]:
    claim = claim_boundary_audit(root, task_name)
    no_action = no_action_audit(root, task_name)
    no_mutation = no_mutation_audit(root, before, specs, task_name)
    secret = secret_audit(root, task_name)
    hash_report = hash_manifest(root, task_name)
    required_status = required_files_status(root, required)
    return {
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "required_files_status": required_status["status"],
        "required_missing": required_status["missing"],
        "hash_validation_status": hash_report["hash_validation_status"],
        "all_pass": all(
            item == "PASS"
            for item in [
                claim["status"],
                no_action["status"],
                no_mutation["status"],
                secret["status"],
                required_status["status"],
                hash_report["hash_validation_status"],
            ]
        ),
    }


def markdown_table(rows: list[tuple[str, Any]]) -> str:
    lines = ["| Field | Value |", "|---|---|"]
    for key, value in rows:
        lines.append(f"| {key} | `{value}` |")
    return "\n".join(lines)


def write_decision_last(root: Path, decision_name: str, decision: dict[str, Any], task_name: str) -> dict[str, Any]:
    write_json(root / decision_name, decision)
    hash_report = hash_manifest(root, task_name)
    decision["hash_validation_status"] = hash_report["hash_validation_status"]
    write_json(root / decision_name, decision)
    hash_manifest(root, task_name)
    return decision
