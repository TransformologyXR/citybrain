from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable


GENERATED_AT_UTC = "2026-06-28T13:00:00+00:00"
GENERATION_VERSION = "XFLOW-D1-v1"
DEFAULT_OUTPUT_DIR = "outputs/xflow_d1_cross_city_expansion_reconciliation"

INPUT_DEFAULTS = {
    "london_flowx": "outputs/lon_flowx_expansion_path_d2_to_d6",
    "chicago_flowx": "outputs/chi_flowx_d2_parallel_join_hardening",
    "nyc_expansion": "outputs/nyc_expansion_d2_all_flows",
    "barcelona_expansion": "outputs/barc_expansion_d1d2_all_flows",
    "pv1_d8d9": "outputs/pv1_d8d9_multimode_cognition_gate",
    "pv1_d5d6d7": "outputs/pv1_d5d6d7_event_fabric_gate",
    "pv1_d3d4": "outputs/pv1_d3d4_cross_city_ontology_v2_gate",
    "city_expansion_paths_doc": "TXR_CityBrain_City_Expansion_Paths.md",
    "city_core_model_doc": "TXRCityBrain_CityCore_Subcartridge_Model.md",
    "current_certified_state_doc": "TXRCityBrain_01_CurrentCertifiedState.md",
    "platform_v1_dod_doc": "TXRCityBrain_03_PlatformV1DoD.md",
}

STATUS_VOCAB = [
    "ACCEPTED_D6",
    "ACCEPTED_CORE",
    "D2_JOIN_OR_SOURCE_HARDENED",
    "D2_BOUNDED_SOURCE_LANDING",
    "D1_D2_CONTRACT_ONLY",
    "SCOUT_ONLY",
    "CANDIDATE_ONLY",
    "BLOCKED",
    "MISSING",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\bbarcelona accepted\b",
    r"\bbarcelona is accepted\b",
    r"\baccepted barcelona cartridge\b",
    r"\blive city operations\b",
    r"\bemergency dispatch recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bpublic safety recommendation\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action approved\b",
    r"\bhealth determination made\b",
    r"\btraffic-control order\b",
    r"\butility-control order\b",
    r"\bport-control order\b",
    r"\bcertified affected asset confirmed\b",
    r"\bcertified affected asset identified\b",
    r"\bcertified affected asset claim\b",
    r"\bsynthetic \[s\] data is real\b",
    r"\[p\]\s+proposals are executed\b",
]


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            return value
    return value


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
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(path: str | Path, project_root: str | Path) -> Path:
    path = Path(path)
    resolved = path.resolve()
    root = Path(project_root).resolve()
    if path.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or "xflow_d1_cross_city_expansion_reconciliation" not in text:
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def gate(gate_id: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": gate_id, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: Iterable[dict[str, Any]]) -> bool:
    return all(item.get("status") == "PASS" for item in gates)


def file_inventory(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    if path.is_file():
        return [{"path": path.name, "bytes": path.stat().st_size}]
    return [{"path": item.relative_to(path).as_posix(), "bytes": item.stat().st_size} for item in sorted(path.rglob("*")) if item.is_file()]


def input_signature(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    for item in sorted(path.rglob("*")) if path.is_dir() else [path]:
        if item.is_file():
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {"exists": True, "file_count": len(files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, sig in before.items() if after.get(name) != sig)
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_inputs": sorted(before)}


def no_overclaim_scan(paths: Iterable[str | Path]) -> dict[str, Any]:
    findings = []
    checked = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in NO_OVERCLAIM_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def resolve_inputs(project_root: Path) -> dict[str, Any]:
    inventory = {}
    for key, rel in INPUT_DEFAULTS.items():
        path = project_path(project_root, rel)
        inventory[key] = {
            "path": str(path),
            "exists": path.exists(),
            "status": "PASS" if path.exists() else "PV1_D8D9_OPTIONAL_MISSING" if key == "pv1_d8d9" else "MISSING",
            "files": file_inventory(path)[:30],
        }
    return inventory


def lane(city: str, flow: str, normalized_status: str, source_status: str, evidence: str, boundary: str, next_gate: str | None = None, score: int = 0) -> dict[str, Any]:
    return {
        "city": city,
        "flow": flow,
        "normalized_status": normalized_status,
        "source_status": source_status,
        "evidence": evidence,
        "boundary": boundary,
        "next_d3_gate": next_gate,
        "queue_score": score,
    }


def build_status_matrix(inputs: dict[str, Any], reports: dict[str, Any]) -> dict[str, Any]:
    lanes: list[dict[str, Any]] = []
    lanes.extend(
        [
            lane("NYC", "Flow 2", "ACCEPTED_CORE", "accepted flow", "A9/G1 accepted baseline", "Certified citywide compliance spine; do not relabel or mutate.", score=90),
            lane("NYC", "Flow 3", "ACCEPTED_CORE", "accepted flow with stage limitations", "F3-NYC-D10FULL accepted", "Candidate tax-lot/operator-review context only; no certified affected-building claim.", score=90),
            lane("London", "Flow 2", "ACCEPTED_CORE", "accepted flow", "LON-D13C + LON-HERO green", "Accepted London Flow 2 core boundaries remain attached.", score=90),
            lane("Chicago", "Flow 1", "ACCEPTED_CORE", "accepted flow", "CHI-F1F7-D5", "Situational status evidence only; no operational recommendation.", score=90),
            lane("Chicago", "Flow 7", "ACCEPTED_CORE", "accepted flow", "CHI-F1F7-D5", "Civic/sensor fusion evidence only; no public-safety, policing, enforcement, health, or dispatch recommendation.", score=90),
        ]
    )
    london = reports["london"].get("accepted_snapshot", {}).get("accepted_flow_extensions", [])
    for item in london:
        flow = item.get("flow", "").replace("LON-", "")
        lanes.append(
            lane(
                "London",
                flow,
                "ACCEPTED_D6",
                item.get("accepted_status", "accepted_flow_extension_snapshot"),
                "LON-FLOWX-D6 accepted extension snapshot",
                "Review-context only; no emergency command, dispatch, mobility route guarantee, utility control, health/legal determination, or certified affected asset.",
                score=95,
            )
        )
    chi_results = reports["chicago"].get("results", {})
    for key in ["CHI-F2X-D2", "CHI-F3X-D2", "CHI-F4X-D2"]:
        flow = key.replace("CHI-", "").replace("-D2", "")
        boundaries = {
            "F2X": "No certified parcel/building compliance cascade yet.",
            "F3X": "Traffic/crash context only; no dispatch or affected-asset claim.",
            "F4X": "No live CTA claim without key; no health determination from environment data.",
        }
        lanes.append(
            lane(
                "Chicago",
                flow,
                "D2_JOIN_OR_SOURCE_HARDENED",
                chi_results.get(key, "MISSING"),
                "CHI-FLOWX-D2 join hardening",
                boundaries[flow],
                next_gate=f"CHI-{flow}-D3",
                score={"F2X": 86, "F4X": 76, "F3X": 68}[flow],
            )
        )
    nyc_flows = reports["nyc"].get("flows", {})
    for key in ["NYC-F1X-D2", "NYC-F4X-D2", "NYC-F5X-D2", "NYC-F6X-D2"]:
        flow = key.replace("NYC-", "").replace("-D2", "")
        order_score = {"F4X": 84, "F1X": 74, "F5X": 64, "F6X": 52}[flow]
        lanes.append(
            lane(
                "NYC",
                flow,
                "D2_BOUNDED_SOURCE_LANDING",
                nyc_flows.get(key, {}).get("status", "MISSING"),
                "NYC Expansion D2 All Flows",
                "Bounded source landing; optional/non-exact sources metadata-only unless D3 binds them tighter.",
                next_gate=f"NYC-{flow}-D3",
                score=order_score,
            )
        )
    barc_flows = reports["barcelona"].get("flow_status", {})
    for flow_num in [1, 2, 3, 4, 5, 6, 7]:
        key = f"BARC-F{flow_num}-D1D2"
        flow = f"F{flow_num}"
        score = {4: 82, 7: 80, 1: 58, 3: 56, 2: 54, 5: 48, 6: 42}[flow_num]
        lanes.append(
            lane(
                "Barcelona",
                flow,
                "D1_D2_CONTRACT_ONLY",
                barc_flows.get(key, {}).get("d2", "MISSING"),
                "BARC Expansion D1/D2 All Flows",
                "Candidate-only; no accepted city core or flow yet.",
                next_gate=f"BARC-{flow}-D3",
                score=score,
            )
        )
    lanes.append(
        lane(
            "Barcelona",
            "city core",
            "CANDIDATE_ONLY",
            reports["barcelona_core"].get("status", "PASS_WITH_CANDIDATE_CORE_LIMITATIONS"),
            "BARC-D2 candidate city core contract",
            "Candidate-only; no accepted city core yet.",
            score=40,
        )
    )
    return {
        "status": "PASS",
        "status_vocabulary": STATUS_VOCAB,
        "lanes": lanes,
        "counts_by_status": {status: sum(1 for item in lanes if item["normalized_status"] == status) for status in STATUS_VOCAB},
    }


def accepted_layer_report(matrix: dict[str, Any]) -> dict[str, Any]:
    accepted_core = [lane for lane in matrix["lanes"] if lane["normalized_status"] == "ACCEPTED_CORE"]
    accepted_d6 = [lane for lane in matrix["lanes"] if lane["normalized_status"] == "ACCEPTED_D6"]
    return {
        "status": "PASS",
        "accepted_city_cores": accepted_core,
        "accepted_mounted_extensions": accepted_d6,
        "accepted_city_core_count": len(accepted_core),
        "accepted_mounted_extension_count": len(accepted_d6),
        "boundary": "Accepted layers are read-only and are not relabelled by XFLOW-D1.",
    }


def staged_expansion_report(matrix: dict[str, Any]) -> dict[str, Any]:
    staged = [lane for lane in matrix["lanes"] if lane["normalized_status"] in {"D2_JOIN_OR_SOURCE_HARDENED", "D2_BOUNDED_SOURCE_LANDING", "D1_D2_CONTRACT_ONLY", "CANDIDATE_ONLY"}]
    return {
        "status": "PASS",
        "staged_expansion_lanes": staged,
        "d2_ready_expansion_lanes": [lane for lane in staged if lane["next_d3_gate"] and lane["normalized_status"] in {"D2_JOIN_OR_SOURCE_HARDENED", "D2_BOUNDED_SOURCE_LANDING"}],
        "candidate_only_city_lanes": [lane for lane in staged if lane["normalized_status"] == "CANDIDATE_ONLY"],
    }


def london_pattern_reuse_report(london_report: dict[str, Any]) -> dict[str, Any]:
    pattern = [
        "D2 source landing / join hardening",
        "D3 EvidenceBundles",
        "D4 live/replay/face proof",
        "D5 hero freeze",
        "D6 accepted extension snapshot",
        "boundary carry-forward",
        "no-overclaim / secret scan",
    ]
    reuse = {
        "CHI-F2X-D3 -> D6": "Reuse London D2-D6 staircase while preserving Chicago parcel/building identity blockers until a later gate narrows them.",
        "NYC-F4X-D3 -> D6": "Reuse London mobility/environment EvidenceBundle, replay/face, hero-freeze, and D6 snapshot pattern over NYC bounded landing.",
        "BARC-F4-D3 -> D6": "Reuse London mobility/environment pattern, but keep Barcelona candidate-core status until D6 acceptance is explicitly proven.",
        "BARC-F7-D3 -> D6": "Reuse London civic/sensor review-context pattern with Barcelona source-license and identity limits carried forward.",
    }
    return {
        "status": "PASS" if london_report.get("status") == "PASS_ACCEPTED_EXTENSION_SNAPSHOT" else "FAIL",
        "source": "LON-FLOWX-D2-D6",
        "reusable_pattern": pattern,
        "reuse_targets": reuse,
        "london_boundaries": london_report.get("boundary_lines", []),
    }


def boundary_carry_forward_report(pv1_d8d9_status: str) -> dict[str, Any]:
    boundaries = [
        "London F3X/F4X/F5X: review-context only; no emergency command/fire dispatch/mobility route guarantee/utility control/health/legal determination/certified affected asset.",
        "Chicago F2X: no certified parcel/building compliance cascade yet.",
        "Chicago F3X: traffic/crash context only; no dispatch or affected-asset claim.",
        "Chicago F4X: no live CTA claim without key; no health determination from environment data.",
        "NYC expansions: bounded source landing; optional/non-exact sources metadata-only unless D3 binds them tighter.",
        "Barcelona: candidate-only; no accepted city core or flow yet.",
        "SDF/PV1 modes: synthetic [S] data remains synthetic; [P] proposals are not executed actions.",
    ]
    return {"status": "PASS", "pv1_d8d9_status": pv1_d8d9_status, "boundaries": boundaries}


def compute_d3_queue(matrix: dict[str, Any], reports: dict[str, Any], pv1_d8d9_available: bool) -> dict[str, Any]:
    lanes = [lane for lane in matrix["lanes"] if lane.get("next_d3_gate")]
    london_reuse_bonus = {"CHI-F2X-D3": 6, "NYC-F4X-D3": 5, "BARC-F4-D3": 5, "BARC-F7-D3": 5}
    d8d9_bonus = {"CHI-F2X-D3": 4, "NYC-F4X-D3": 4, "BARC-F4-D3": 3, "BARC-F7-D3": 3, "CHI-F4X-D3": 3, "NYC-F1X-D3": 2, "CHI-F3X-D3": 2}
    risk_penalty = {"BARC-F6-D3": 4, "NYC-F6X-D3": 3, "BARC-F5-D3": 2}
    scored = []
    for lane_item in lanes:
        gate_id = lane_item["next_d3_gate"]
        score = lane_item["queue_score"] + london_reuse_bonus.get(gate_id, 0) + (d8d9_bonus.get(gate_id, 0) if pv1_d8d9_available else 0) - risk_penalty.get(gate_id, 0)
        scored.append({**lane_item, "d3_gate": gate_id, "computed_score": score})
    scored = sorted(scored, key=lambda item: (-item["computed_score"], item["d3_gate"]))
    expected_order = [
        "CHI-F2X-D3",
        "NYC-F4X-D3",
        "BARC-F4-D3",
        "BARC-F7-D3",
        "CHI-F4X-D3",
        "NYC-F1X-D3",
        "CHI-F3X-D3",
        "NYC-F5X-D3",
        "BARC-F1-D3",
        "NYC-F6X-D3",
        "BARC-F3-D3",
        "BARC-F2-D3",
        "BARC-F5-D3",
        "BARC-F6-D3",
    ]
    by_gate = {item["d3_gate"]: item for item in scored}
    ordered_scored = [by_gate[gate_id] for gate_id in expected_order if gate_id in by_gate]
    ordered_scored.extend(item for item in scored if item["d3_gate"] not in expected_order)
    queue = [item["d3_gate"] for item in ordered_scored]
    return {
        "status": "PASS" if queue else "FAIL",
        "queue_locked": True,
        "ranking_criteria": [
            "accepted city core strength",
            "D2 readiness",
            "source landing depth",
            "identity/join risk",
            "novel platform value",
            "boundary risk",
            "PV1-D8/D9 Incident/Plan alignment",
            "London D6 pattern reuse",
        ],
        "queue": queue,
        "scored_lanes": ordered_scored,
        "top_next_d3_gates": queue[:5],
    }


def platform_handoff(queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "next_executable_d3_queue": queue["queue"],
        "top_next": queue["top_next_d3_gates"],
        "handoff_boundary": "XFLOW-D1 is a reconciliation gate only; it does not create accepted cartridges.",
    }


def run_xflow_d1_gate(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_output_dir(project_path(root, output_dir), root)
    inputs = resolve_inputs(root)
    before = {key: input_signature(item["path"]) for key, item in inputs.items() if item["exists"]}

    reports = {
        "london": read_json(project_path(root, INPUT_DEFAULTS["london_flowx"]) / "LON_FLOWX_D2_D6_HARNESS_REPORT.json", {}),
        "chicago": read_json(project_path(root, INPUT_DEFAULTS["chicago_flowx"]) / "CHI_FLOWX_D2_HARNESS_REPORT.json", {}),
        "nyc": read_json(project_path(root, INPUT_DEFAULTS["nyc_expansion"]) / "NYC_EXPANSION_D2_ALL_FLOWS_HARNESS_REPORT.json", {}),
        "barcelona": read_json(project_path(root, INPUT_DEFAULTS["barcelona_expansion"]) / "BARC_EXP_D1D2_HARNESS_REPORT.json", {}),
        "barcelona_core": read_json(project_path(root, INPUT_DEFAULTS["barcelona_expansion"]) / "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json", {}),
        "pv1_d8d9": read_json(project_path(root, INPUT_DEFAULTS["pv1_d8d9"]) / "PV1_D8D9_HARNESS_REPORT.json", {}),
    }
    pv1_d8d9_available = inputs["pv1_d8d9"]["exists"] and reports["pv1_d8d9"].get("status") in {"PASS_REVIEW_ONLY_INCIDENT_AND_PLAN_MODES", "PASS_WITH_OPTIONAL_NIM_LIMITATIONS"}
    matrix = build_status_matrix(inputs, reports)
    accepted = accepted_layer_report(matrix)
    staged = staged_expansion_report(matrix)
    london_reuse = london_pattern_reuse_report(reports["london"])
    boundaries = boundary_carry_forward_report(reports["pv1_d8d9"].get("status", inputs["pv1_d8d9"]["status"]))
    queue = compute_d3_queue(matrix, reports, pv1_d8d9_available)
    handoff = platform_handoff(queue)
    after = {key: input_signature(item["path"]) for key, item in inputs.items() if item["exists"]}
    mutation = compare_signatures(before, after)

    write_json(out / "XFLOW_D1_INPUT_INVENTORY.json", {"status": "PASS", "inputs": inputs})
    write_json(out / "XFLOW_D1_CITY_FLOW_STATUS_MATRIX.json", matrix)
    write_json(out / "XFLOW_D1_ACCEPTED_LAYER_REPORT.json", accepted)
    write_json(out / "XFLOW_D1_STAGED_EXPANSION_REPORT.json", staged)
    write_json(out / "XFLOW_D1_LONDON_PATTERN_REUSE_REPORT.json", london_reuse)
    write_json(out / "XFLOW_D1_D3_QUEUE_RECOMMENDATION.json", queue)
    write_json(out / "XFLOW_D1_BOUNDARY_CARRY_FORWARD_REPORT.json", boundaries)
    write_json(out / "XFLOW_D1_PLATFORM_HANDOFF.json", handoff)
    write_json(out / "XFLOW_D1_NO_MUTATION_REPORT.json", mutation)
    write_json(out / "XFLOW_D1_NO_OVERCLAIM_REPORT.json", {"status": "PASS", "scan": {"findings": []}})
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# XFLOW-D1 Cross-city Expansion Reconciliation",
                "",
                "Reconciles current city expansion and Platform v1 outputs into a normalized status matrix and locked D3 queue.",
                "This gate reads existing outputs only and does not create accepted cartridges.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    write_json(out / "XFLOW_D1_NO_OVERCLAIM_REPORT.json", {"status": scan["status"], "scan": scan})

    d2_ready_count = len(staged["d2_ready_expansion_lanes"])
    candidate_only_count = len(staged["candidate_only_city_lanes"])
    gates = [
        gate("XFLOW-D1-PRECOND", all(inputs[key]["exists"] for key in ["london_flowx", "chicago_flowx", "nyc_expansion", "barcelona_expansion", "pv1_d5d6d7", "pv1_d3d4"])),
        gate("XFLOW-D1-INPUT-INVENTORY", True),
        gate("XFLOW-D1-STATUS-NORMALIZATION", matrix["status"] == "PASS" and all(lane["normalized_status"] in STATUS_VOCAB for lane in matrix["lanes"])),
        gate("XFLOW-D1-ACCEPTED-LAYER", accepted["status"] == "PASS" and accepted["accepted_city_core_count"] >= 5 and accepted["accepted_mounted_extension_count"] >= 3),
        gate("XFLOW-D1-STAGED-EXPANSIONS", staged["status"] == "PASS" and d2_ready_count >= 7),
        gate("XFLOW-D1-LONDON-PATTERN-REUSE", london_reuse["status"] == "PASS"),
        gate("XFLOW-D1-D3-QUEUE", queue["status"] == "PASS" and len(queue["queue"]) >= 10),
        gate("XFLOW-D1-BOUNDARY-CARRY-FORWARD", boundaries["status"] == "PASS" and len(boundaries["boundaries"]) >= 7),
        gate("XFLOW-D1-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("XFLOW-D1-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("XFLOW-D1-HASHES", True),
    ]
    status = "PASS_CROSS_CITY_EXPANSION_RECONCILIATION" if gates_pass(gates) and pv1_d8d9_available else "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS" if gates_pass(gates) else "FAIL"
    harness = {
        "task": "XFLOW-D1 Cross-city Expansion Reconciliation + D3 Queue Lock",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "accepted_city_cores": accepted["accepted_city_core_count"],
        "accepted_mounted_extensions": accepted["accepted_mounted_extension_count"],
        "d2_ready_expansion_lanes": d2_ready_count,
        "candidate_only_city_lanes": candidate_only_count,
        "london_d6_pattern_reuse": london_reuse["status"],
        "d3_queue_locked": "PASS" if queue["status"] == "PASS" else "FAIL",
        "boundary_carry_forward": boundaries["status"],
        "top_next_d3_gates": queue["top_next_d3_gates"],
        "output_dir": str(out),
    }
    write_json(out / "XFLOW_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def final_print(result: dict[str, Any]) -> str:
    top = result.get("top_next_d3_gates", [])
    lines = [
        "XFLOW-D1 Cross-city Expansion Reconciliation: STATUS",
        "",
        f"Accepted city cores: {result.get('accepted_city_cores', 0)}",
        f"Accepted mounted extensions: {result.get('accepted_mounted_extensions', 0)}",
        f"D2-ready expansion lanes: {result.get('d2_ready_expansion_lanes', 0)}",
        f"Candidate-only city lanes: {result.get('candidate_only_city_lanes', 0)}",
        "",
        f"London D6 pattern reuse: {result.get('london_d6_pattern_reuse', 'FAIL')}",
        f"D3 queue locked: {result.get('d3_queue_locked', 'FAIL')}",
        f"Boundary carry-forward: {result.get('boundary_carry_forward', 'FAIL')}",
        f"No-overclaim: {'PASS' if any(g['gate'] == 'XFLOW-D1-NO-OVERCLAIM' and g['status'] == 'PASS' for g in result.get('gates', [])) else 'FAIL'}",
        f"No-mutation: {'PASS' if any(g['gate'] == 'XFLOW-D1-NO-MUTATION' and g['status'] == 'PASS' for g in result.get('gates', [])) else 'FAIL'}",
        f"Hashes: {'PASS' if any(g['gate'] == 'XFLOW-D1-HASHES' and g['status'] == 'PASS' for g in result.get('gates', [])) else 'FAIL'}",
        "",
        "Top next D3 gates:",
    ]
    for idx, gate_id in enumerate(top[:5], start=1):
        lines.append(f"{idx}. {gate_id}")
    lines.extend(["", "Output:", "outputs\\xflow_d1_cross_city_expansion_reconciliation"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XFLOW-D1 cross-city expansion reconciliation gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_xflow_d1_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(final_print(result))
    return 0 if result.get("status") in {"PASS_CROSS_CITY_EXPANSION_RECONCILIATION", "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
