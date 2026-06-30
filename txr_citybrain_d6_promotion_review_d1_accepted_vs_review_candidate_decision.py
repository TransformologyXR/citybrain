#!/usr/bin/env python3
"""D6-PROMOTION-REVIEW-D1 accepted vs review/candidate decision."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D6-PROMOTION-REVIEW-D1 Accepted vs Review/Candidate Decision"
DEFAULT_OUTPUT_DIR = "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision"
PASS_STATUSES = {"PASS_D6_PROMOTION_REVIEW", "PASS_WITH_REVIEW_ONLY_DECISIONS", "PASS_WITH_CANDIDATE_LIMITATIONS"}

LANES = {
    "CHI-F4X-D6": {
        "source_d5": "outputs/chi_f4x_d5_hero_freeze_package",
        "prefix": "CHI_F4X_D5",
        "city": "Chicago",
        "flow": "F4X",
        "decision": "REVIEW_PROMOTION_READY_NOT_ACCEPTED",
        "reason": "D4/D5 are payload-only; live/face route acceptance boundary is unresolved.",
    },
    "NYC-F1X-D6": {
        "source_d5": "outputs/nyc_f1x_d5_situational_status_hero_freeze_package",
        "prefix": "NYC_F1X_D5",
        "city": "NYC",
        "flow": "F1X",
        "decision": "REVIEW_PROMOTION_READY_NOT_ACCEPTED",
        "reason": "D4/D5 are payload-only and capped/windowed source limitations carry forward.",
    },
    "CHI-F3X-D6": {
        "source_d5": "outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package",
        "prefix": "CHI_F3X_D5",
        "city": "Chicago",
        "flow": "F3X",
        "decision": "REVIEW_PROMOTION_READY_NOT_ACCEPTED",
        "reason": "Traffic/crash context remains review-only; no dispatch, public-safety, or affected-asset claim.",
    },
    "NYC-F5X-D6": {
        "source_d5": "outputs/nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package",
        "prefix": "NYC_F5X_D5",
        "city": "NYC",
        "flow": "F5X",
        "decision": "REVIEW_PROMOTION_READY_NOT_ACCEPTED",
        "reason": "Risk context remains review-only; no utility-control, emergency-response, or certified infrastructure claim.",
    },
    "NYC-F6X-D6": {
        "source_d5": "outputs/nyc_f6x_d5_port_airport_logistics_hero_freeze_package",
        "prefix": "NYC_F6X_D5",
        "city": "NYC",
        "flow": "F6X",
        "decision": "REVIEW_PROMOTION_READY_NOT_ACCEPTED",
        "reason": "Logistics context remains review-only; no port/airport operational command or safety-critical sequencing.",
    },
    "BARC-F7-D6": {
        "source_d5": "outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package",
        "prefix": "BARC_F7_D5",
        "city": "Barcelona",
        "flow": "F7",
        "decision": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "reason": "Barcelona city core remains candidate-only; Flow 7 cannot be accepted without city-core acceptance policy.",
    },
}

INPUTS = {
    "d5_batch": "outputs/d5_batch_d1_hero_freeze_packages",
    "d4_batch": "outputs/d4_batch_d1_remaining_replay_face_proofs",
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "flowx_face_publish_smoke_d1_optional": "outputs/flowx_face_publish_smoke_d1",
    "ontology_v2": "contracts/ontology_v2",
}

REQUIRED = [
    "README.md",
    "D6_PROMOTION_REVIEW_D1_HARNESS_REPORT.json",
    "D6_PROMOTION_REVIEW_D1_INPUT_INVENTORY.json",
    "D6_PROMOTION_REVIEW_D1_DECISION_MATRIX.json",
    "D6_PROMOTION_REVIEW_D1_PROMOTION_REVIEW_REPORT.json",
    "D6_PROMOTION_REVIEW_D1_ACCEPTANCE_BLOCKER_REPORT.json",
    "D6_PROMOTION_REVIEW_D1_CANDIDATE_REVIEW_SNAPSHOTS.json",
    "D6_PROMOTION_REVIEW_D1_NEXT_ACTIONS.json",
    "D6_PROMOTION_REVIEW_D1_NO_OVERCLAIM_REPORT.json",
    "D6_PROMOTION_REVIEW_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\ball flows accepted\b",
    r"\bbarcelona accepted\b",
    r"\bchicago flow 4 accepted\b",
    r"\bnyc flow 1 accepted\b",
    r"\bchicago flow 3 .* accepted\b",
    r"\bnyc flow 5 accepted\b",
    r"\bnyc flow 6 accepted\b",
    r"\bbarcelona flow 7 accepted\b",
    r"\bpayload-only means live route\b",
    r"\bcapped bulk is full\b",
    r"\bwindowed/api snapshot is historical completeness\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\bemergency dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bhealth determination\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\butility-control instruction\b",
    r"\bport/airport operational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "candidate-only", "review-only", "blocked")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "d6_promotion_review_d1_accepted_vs_review_candidate_decision":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "D6_PROMOTION_REVIEW_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 72) : match.end() + 24]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def inventory(project_root: Path) -> dict[str, Any]:
    inputs = {name: project_path(project_root, rel) for name, rel in INPUTS.items()}
    inputs.update({lane: project_path(project_root, cfg["source_d5"]) for lane, cfg in LANES.items()})
    return {
        "status": "PASS",
        "inputs": {
            name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)}
            for name, path in inputs.items()
        },
    }


def flowx_publish_status(project_root: Path, lane: str) -> dict[str, Any]:
    path = project_path(project_root, "outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_LANE_STATUS_MATRIX.json")
    matrix = read_json(path, {})
    base_lane = lane.replace("-D6", "")
    for row in matrix.get("lanes", []):
        if row.get("lane") == base_lane:
            return row
    return {
        "lane": base_lane,
        "published_review_route": False,
        "to_face_route_status": "FACE_ROUTE_PAYLOAD_ONLY",
        "to_face_hero_status": "FACE_HERO_PAYLOAD_ONLY",
        "smoke_status": "NOT_RUN",
    }


def lane_decision(project_root: Path, lane: str, cfg: dict[str, Any]) -> dict[str, Any]:
    d5_dir = project_path(project_root, cfg["source_d5"])
    harness = read_json(d5_dir / f"{cfg['prefix']}_HARNESS_REPORT.json", {})
    freeze = read_json(d5_dir / f"{cfg['prefix']}_HERO_FREEZE_PACKAGE.json", {})
    source_face_status = harness.get("face_hero_status") or freeze.get("face_hero_status") or "UNKNOWN"
    publish = flowx_publish_status(project_root, lane)
    route_status = publish.get("to_face_route_status") or "FACE_ROUTE_PAYLOAD_ONLY"
    published_review_route = bool(publish.get("published_review_route")) and publish.get("smoke_status") == "PASS"
    face_status = publish.get("to_face_hero_status") if published_review_route else source_face_status
    payload_only = not published_review_route and source_face_status == "FACE_HERO_PAYLOAD_ONLY"
    accepted = False
    blockers = []
    if payload_only:
        blockers.append("D4/D5 face route is payload-only, not a live published and smoked route.")
    if published_review_route:
        blockers.append("Published review route passed smoke, but publish/smoke is not an acceptance criterion by itself.")
    if cfg["city"] == "Barcelona":
        blockers.append("Barcelona city core remains candidate-only.")
    blockers.append("Separate acceptance criteria are not satisfied by D5 hero freeze alone.")
    return {
        "lane": lane,
        "city": cfg["city"],
        "flow": cfg["flow"],
        "source_d5": str(d5_dir),
        "d5_status": harness.get("status"),
        "source_face_hero_status": source_face_status,
        "face_hero_status": face_status,
        "face_route_status": route_status,
        "published_review_route": published_review_route,
        "flowx_publish_smoke_status": publish.get("smoke_status"),
        "hero_count": harness.get("selected_heroes"),
        "decision": cfg["decision"],
        "accepted_flow_cartridge": accepted,
        "review_context_only": True,
        "candidate_only": cfg["decision"].startswith("CANDIDATE"),
        "reason": (
            "Published review route is smoked, but this D6 gate remains review-only and does not accept flows."
            if published_review_route and not cfg["decision"].startswith("CANDIDATE")
            else cfg["reason"]
        ),
        "acceptance_blockers": blockers,
        "next_step": (
            "Hold for explicit acceptance policy/criteria; do not accept from publish/smoke alone."
            if published_review_route
            else "Hold for future live-route/smoke or city-core policy work; do not accept from payload-only D5."
        ),
    }


def run_d6_promotion_review(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in INPUTS.items()}
    watched.update({lane: project_path(project_root, cfg["source_d5"]) for lane, cfg in LANES.items()})
    before = {name: input_signature(path) for name, path in watched.items()}

    inv = inventory(project_root)
    decisions = [lane_decision(project_root, lane, cfg) for lane, cfg in LANES.items()]
    accepted_count = sum(1 for d in decisions if d["accepted_flow_cartridge"])
    matrix = {"status": "PASS", "decisions": decisions}
    review = {
        "status": "PASS_WITH_REVIEW_ONLY_DECISIONS",
        "accepted_count": accepted_count,
        "review_ready_count": sum(1 for d in decisions if d["decision"] == "REVIEW_PROMOTION_READY_NOT_ACCEPTED"),
        "candidate_only_count": sum(1 for d in decisions if d["candidate_only"]),
        "published_review_route_count": sum(1 for d in decisions if d["published_review_route"]),
        "decision_summary": "All six lanes are promotion-reviewed conservatively. None are accepted; published review routes remove the payload-only blocker where present but do not satisfy acceptance criteria by themselves.",
    }
    blockers = {
        "status": "PASS",
        "blockers": [
            {"lane": d["lane"], "acceptance_blockers": d["acceptance_blockers"]}
            for d in decisions
        ],
    }
    snapshots = {
        "status": "PASS",
        "snapshots": [
            {
                "lane": d["lane"],
                "snapshot_status": "CANDIDATE_REVIEW_SNAPSHOT" if d["candidate_only"] else "REVIEW_PROMOTION_READY_SNAPSHOT",
                "accepted_flow_cartridge": False,
                "published_review_route": d["published_review_route"],
                "source_d5": d["source_d5"],
            }
            for d in decisions
        ],
    }
    next_actions = {
        "status": "PASS",
        "items": [
            {"rank": 1, "action": "Resolve explicit acceptance criteria for lanes with smoked published review routes; publish/smoke alone does not accept a flow."},
            {"rank": 2, "action": "Keep Barcelona Flow 7 candidate-only until Barcelona city-core acceptance policy is resolved."},
            {"rank": 3, "action": "Do not mark any reviewed lane accepted from this D6 gate."},
        ],
    }

    write_json(out / "D6_PROMOTION_REVIEW_D1_INPUT_INVENTORY.json", inv)
    write_json(out / "D6_PROMOTION_REVIEW_D1_DECISION_MATRIX.json", matrix)
    write_json(out / "D6_PROMOTION_REVIEW_D1_PROMOTION_REVIEW_REPORT.json", review)
    write_json(out / "D6_PROMOTION_REVIEW_D1_ACCEPTANCE_BLOCKER_REPORT.json", blockers)
    write_json(out / "D6_PROMOTION_REVIEW_D1_CANDIDATE_REVIEW_SNAPSHOTS.json", snapshots)
    write_json(out / "D6_PROMOTION_REVIEW_D1_NEXT_ACTIONS.json", next_actions)
    gates = [
        {"gate": "D6-PROMOTION-REVIEW-D1-PRECOND", "status": "PASS" if all(d.get("d5_status", "").startswith("PASS") for d in decisions) else "FAIL"},
        {"gate": "INPUT-INVENTORY", "status": inv["status"]},
        {"gate": "DECISION-MATRIX", "status": matrix["status"]},
        {"gate": "PROMOTION-REVIEW", "status": "PASS"},
        {"gate": "ACCEPTANCE-BLOCKERS", "status": blockers["status"]},
        {"gate": "CANDIDATE-REVIEW-SNAPSHOTS", "status": snapshots["status"]},
        {"gate": "NEXT-ACTIONS", "status": next_actions["status"]},
        {"gate": "NO-ACCEPTED-FLOW-FROM-PUBLISH-SMOKE", "status": "PASS" if accepted_count == 0 else "FAIL"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "D6_PROMOTION_REVIEW_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "D6_PROMOTION_REVIEW_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NO-MUTATION", "status": mutation["status"]})

    status = "PASS_WITH_REVIEW_ONLY_DECISIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(
        out / "README.md",
        "# D6-PROMOTION-REVIEW-D1 Accepted vs Review/Candidate Decision\n\n"
        f"Status: `{status}`\n\n"
        "All D4/D5 lanes remain review-ready or candidate-only. Published review routes are not accepted flows.\n",
    )
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "accepted_count": accepted_count,
        "decision_count": len(decisions),
        "decisions": decisions,
        "gates": gates,
    }
    write_json(out / "D6_PROMOTION_REVIEW_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in REQUIRED if p != "SHA256SUMS.json")
    gates.append({"gate": "HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_WITH_REVIEW_ONLY_DECISIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "D6_PROMOTION_REVIEW_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "# D6-PROMOTION-REVIEW-D1 Accepted vs Review/Candidate Decision\n\n"
        f"Status: `{status}`\n\n"
        "All D4/D5 lanes remain review-ready or candidate-only. Published review routes are not accepted flows.\n",
    )
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"D6-PROMOTION-REVIEW-D1 Accepted vs Review/Candidate Decision: {report['status']}")
    print()
    for decision in report["decisions"]:
        print(f"{decision['lane']}: {decision['decision']}")
    print()
    print(f"Accepted flows: {report['accepted_count']}")
    print(f"Published review routes: {sum(1 for decision in report['decisions'] if decision.get('published_review_route'))}")
    gate_map = {g["gate"]: g["status"] for g in report["gates"]}
    print(f"No accepted flow from publish/smoke: {gate_map.get('NO-ACCEPTED-FLOW-FROM-PUBLISH-SMOKE')}")
    print(f"No-overclaim: {gate_map.get('NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run D6 promotion review accepted vs review/candidate decision")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_d6_promotion_review(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
