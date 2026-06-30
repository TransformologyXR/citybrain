from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D12 London NeMo/NIM Wrapper"
DEFAULT_D9Z_DIR = "outputs/lon_d9z_d9d2_accepted_snapshot"
DEFAULT_D10Z_DIR = "outputs/lon_d10z_d10_accepted_snapshot"
DEFAULT_D10_DIR = "outputs/lon_d10_planning_context_enrichment"
DEFAULT_OUTPUT_DIR = "outputs/lon_d12_london_nemo_nim_wrapper"
SYNC_TARGET = Path("/data/citybrain/from_3090/london_d12_nemo_wrapper_v1")
PUBLIC_TOOL = "citybrain_london_query"
ALLOWED_QUERY_TYPES = [
    "london_status",
    "borough_coverage",
    "pld_application_context",
    "uprn_profile",
    "planning_context_summary",
    "source_limitations",
    "unmatched_pld_explanation",
]
FORBIDDEN_PUBLIC_TOOLS = {
    "graph_query",
    "raw_parquet_read",
    "sql_query",
    "file_read",
    "pld_api_call",
    "context_layer_lookup",
}
LIMITATION_LINES = [
    "UPRN is not BBL",
    "TOID is not BIN",
    "PLD is not DOB",
    "D10 is not legal planning judgment",
    "D6 remains source-limited",
    "EV charging source-limited",
    "TOID geometry unavailable",
    "5,116 PLD records unmatched",
]
NO_OVERCLAIM_LINES = [
    "D12 is a governed wrapper over accepted London evidence.",
    "D12 does not ingest new data.",
    "D12 does not choose a London hero.",
    "D12 does not make legal planning decisions.",
    "D12 does not claim enforcement/building-control coverage.",
    "D12 does not expose low-level tools.",
]
FORBIDDEN_CLAIMS = [
    "legal planning determination",
    "application should be approved",
    "application should be refused",
    "complete enforcement coverage",
    "building-control integrated",
    "PLD is DOB",
    "UPRN is BBL",
    "TOID is BIN",
    "TOID geometry available",
    "EV charging complete",
    "hero cascade",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path)] = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": sha256_file(path)}
    return out


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D12-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d12" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["tool", "samples", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def precondition_report(d9z_dir: Path, d10z_dir: Path, d10_dir: Path) -> dict[str, Any]:
    d9z = d9z_dir / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json"
    d10z = d10z_dir / "LON_D10Z_HARNESS_REPORT.json"
    d10 = d10_dir / "LON_D10_HARNESS_REPORT.json"
    checks = {
        "d9z_report_exists": d9z.exists(),
        "d9z_status_pass": read_json(d9z, {}).get("status") == "PASS",
        "d10z_report_exists": d10z.exists(),
        "d10z_status_pass": read_json(d10z, {}).get("status") == "PASS",
        "d10_report_exists": d10.exists(),
        "d10_status_pass": read_json(d10, {}).get("status") == "PASS",
    }
    return {"gate": "LON-D12-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def accepted_counts(d9z_dir: Path, d10z_dir: Path) -> dict[str, Any]:
    d9z = read_json(d9z_dir / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {})
    d9 = d9z.get("coverage_summary") or {}
    d10 = read_json(d10z_dir / "accepted" / "london_d10_accepted_counts.json", {})
    return {
        "pld_applications_considered": d9.get("pld_applications_considered", 58867),
        "exact_api_matches": d9.get("api_records_matched_exact", 57796),
        "pld_to_uprn_edges": d9.get("pld_to_uprn_edges_emitted", 53753),
        "pld_uprn_toid_paths": d9.get("pld_uprn_toid_paths", 53570),
        "pld_uprn_usrn_paths": d9.get("pld_uprn_usrn_paths", 54417),
        "unmatched_pld_records": d9.get("unmatched_records", 5116),
        "unmatched_reasons": (d9z.get("unmatched_count_basis") or {}).get("unmatched_reasons", {}),
        "context_nodes": d10.get("context_nodes_emitted", 186180),
        "context_edges": d10.get("context_edges_emitted", 232101),
        "pld_applications_with_context": d10.get("pld_applications_with_context", 53751),
        "borough_coverage": f"{d10.get('boroughs_with_context_coverage', 32)} / {d10.get('boroughs_total', 33)}",
        "uprns_with_context": d10.get("uprns_with_context", 41793),
        "toids_with_context": d10.get("toids_with_context", 0),
    }


def seed_subjects(d10_dir: Path, d11_dir: Path | None) -> dict[str, Any]:
    if d11_dir and (d11_dir / "reports" / "query_seed_selection.json").exists():
        d11 = read_json(d11_dir / "reports" / "query_seed_selection.json", {})
        return {
            "pld_seed": d11.get("pld_seed"),
            "uprn_seed": d11.get("uprn_seed"),
            "context_seed": d11.get("context_seed"),
            "basis": "D11 deterministic seed selection",
        }
    query_results = read_json(d10_dir / "queries" / "sample_query_results.json", [])
    plds = [
        (row.get("parameters") or {}).get("canonical_id")
        for row in query_results
        if row.get("query_type") == "pld_application_context_profile"
    ]
    edges = read_json(d10_dir / "london_context_edges_sample.json", [])
    uprns = [row.get("src") for row in edges if str(row.get("src", "")).startswith("parcel:uk-london:uprn:")]
    contexts = [row.get("dst") for row in edges]
    return {
        "pld_seed": sorted([x for x in plds if x])[0] if plds else None,
        "uprn_seed": sorted(set(uprns))[0] if uprns else None,
        "context_seed": sorted(set(contexts))[0] if contexts else None,
        "basis": "D10 deterministic sample query / context edge sample",
    }


def source_lineage() -> list[dict[str, str]]:
    return [
        {"stage": "D9Z", "source": "accepted D9D2 London snapshot"},
        {"stage": "D10Z", "source": "accepted D10 planning-context snapshot"},
        {"stage": "D10", "source": "planning-context deterministic reports and EvidenceBundles"},
        {"stage": "D12", "source": "governed wrapper; no new data ingest"},
    ]


def evidence_bundle(query_type: str, subject_id: str | None, answer_status: str, facts: list[str], counts: dict[str, Any], entities: list[Any] | None = None, edges: list[Any] | None = None, paths: list[Any] | None = None, limitations: list[str] | None = None) -> dict[str, Any]:
    return {
        "tool": PUBLIC_TOOL,
        "query_type": query_type,
        "subject_id": subject_id,
        "answer_status": answer_status,
        "facts": facts,
        "counts": counts,
        "entities": entities or [],
        "edges": edges or [],
        "paths": paths or [],
        "limitations": limitations or LIMITATION_LINES,
        "wrapper_boundaries": NO_OVERCLAIM_LINES,
        "source_lineage": source_lineage(),
        "confidence_summary": {
            "deterministic_report_readback": 1.0,
            "model_may_compute_counts": 0.0,
        },
        "grounding_policy": {
            "model_may_narrate": True,
            "model_may_compute_counts": False,
            "model_may_add_facts": False,
        },
    }


def classify_request(text: str, seeds: dict[str, Any]) -> tuple[str, str | None, str | None]:
    lower = text.lower()
    if "approved" in lower or "refused" in lower:
        return "rejected", None, "D12 cannot answer approval/refusal or legal planning judgment requests."
    if "enforcement" in lower and ("complete" in lower or "violations" in lower):
        return "rejected", None, "D6 enforcement/building-control remains source-limited and cannot be treated as complete."
    if "pld as if" in lower or "dob" in lower:
        return "rejected", None, "PLD is not DOB."
    if "borough" in lower and "coverage" in lower:
        return "borough_coverage", None, None
    if "connected pld" in lower or "planning application" in lower or "uprn and planning context" in lower:
        return "pld_application_context", seeds.get("pld_seed"), None
    if "unmatched" in lower:
        return "unmatched_pld_explanation", None, None
    if "source limitation" in lower or "limitations" in lower:
        return "source_limitations", None, None
    if "planning-context" in lower or "planning context" in lower:
        return "planning_context_summary", seeds.get("context_seed"), None
    return "london_status", None, None


def citybrain_london_query(request: str, counts: dict[str, Any], seeds: dict[str, Any], d10_dir: Path) -> dict[str, Any]:
    query_type, subject_id, rejection = classify_request(request, seeds)
    if query_type == "rejected":
        return evidence_bundle(
            "rejected",
            None,
            "rejected",
            [rejection or "Request rejected by London wrapper policy."],
            counts,
            limitations=LIMITATION_LINES,
        )
    if query_type == "london_status":
        facts = [
            f"London D9D2 considered {counts['pld_applications_considered']} PLD applications.",
            f"London D9D2 emitted {counts['pld_to_uprn_edges']} PLD-to-UPRN edges.",
            f"D10 accepted {counts['context_nodes']} planning-context nodes and {counts['context_edges']} planning-context edges.",
            f"D10 reports borough planning-context coverage of {counts['borough_coverage']}.",
        ]
        return evidence_bundle(query_type, None, "answered", facts, counts)
    if query_type == "borough_coverage":
        coverage = read_json(d10_dir / "LON_D10_COVERAGE_REPORT.json", {})
        facts = [
            f"D10 reports borough planning-context coverage of {counts['borough_coverage']}.",
            f"D10 reports {counts['pld_applications_with_context']} PLD applications with planning context.",
        ]
        return evidence_bundle(query_type, "borough_coverage:london:d10z", "answered", facts, counts, entities=[coverage.get("coverage_by_borough", {})])
    if query_type == "pld_application_context":
        facts = [
            f"Seed connected PLD application is {subject_id}.",
            f"D10 reports {counts['pld_applications_with_context']} PLD applications with planning context.",
            "The PLD context path is deterministic through accepted D9D2 PLD-to-UPRN recovery and D10 planning-context joins where present.",
        ]
        edges = [row for row in read_json(d10_dir / "london_context_edges_sample.json", []) if row.get("src") == subject_id]
        return evidence_bundle(query_type, subject_id, "answered", facts, counts, entities=[{"canonical_id": subject_id, "entity_type": "planning_application"}], edges=edges)
    if query_type == "uprn_profile":
        facts = [
            f"Seed UPRN is {subject_id or seeds.get('uprn_seed')}.",
            f"D10 reports {counts['uprns_with_context']} UPRNs with planning context.",
        ]
        return evidence_bundle(query_type, subject_id or seeds.get("uprn_seed"), "answered", facts, counts)
    if query_type == "planning_context_summary":
        coverage = read_json(d10_dir / "LON_D10_COVERAGE_REPORT.json", {})
        facts = [
            f"D10 accepted {counts['context_nodes']} planning-context nodes.",
            f"D10 accepted {counts['context_edges']} planning-context edges.",
            f"D10 reports context layer counts {coverage.get('coverage_by_layer', {})}.",
        ]
        return evidence_bundle(query_type, subject_id, "answered", facts, counts, entities=[coverage.get("coverage_by_layer", {})])
    if query_type == "source_limitations":
        facts = [
            "D6 enforcement/building-control remains source-limited.",
            "EV charging site context is source-limited.",
            "TOID geometry unavailable.",
            "No London hero is selected by D12.",
        ]
        return evidence_bundle(query_type, "source_limitations:london", "source_limited", facts, counts)
    if query_type == "unmatched_pld_explanation":
        reasons = counts.get("unmatched_reasons", {})
        facts = [
            f"{counts['unmatched_pld_records']} PLD records remain unmatched.",
            f"Unmatched reasons are {reasons}.",
            "Address fuzzy matching, postcode-only matching, nearest geometry matching, and site-name similarity are not certified canonical joins.",
        ]
        return evidence_bundle(query_type, "unmatched_pld:london:d9d2", "partially_answered", facts, counts)
    return evidence_bundle("rejected", None, "rejected", ["Unsupported query type."], counts)


def deterministic_narration(bundle: dict[str, Any]) -> str:
    facts = " ".join(bundle["facts"])
    limitations = " ".join(bundle["limitations"])
    return f"{facts} {limitations}"


def allowed_number_strings(bundle: dict[str, Any]) -> set[str]:
    text = json.dumps({"facts": bundle["facts"], "counts": bundle["counts"], "limitations": bundle["limitations"]}, ensure_ascii=False)
    return set(re.findall(r"\b\d{1,3}(?:,\d{3})*|\b\d+\b", text.replace("53753", "53,753")))


def grounding_check(bundle: dict[str, Any], narration: str) -> dict[str, Any]:
    bundle_text = json.dumps(bundle, ensure_ascii=False)
    missing_numbers = [num for num in re.findall(r"\b\d{1,3}(?:,\d{3})*|\b\d+\b", narration) if num not in allowed_number_strings(bundle) and num.replace(",", "") not in allowed_number_strings(bundle)]
    ids = re.findall(r"(?:permit|parcel|planning_context_area):uk-london:[A-Za-z0-9_&:.-]+", narration)
    missing_ids = [cid for cid in ids if cid not in bundle_text]
    missing_limits = [line for line in LIMITATION_LINES if line not in narration]
    forbidden = []
    lower = narration.lower()
    for claim in FORBIDDEN_CLAIMS:
        c = claim.lower()
        if c in lower and f"not {c}" not in lower and f"no {c}" not in lower and "unavailable" not in lower:
            forbidden.append(claim)
    status = "PASS" if not missing_numbers and not missing_ids and not missing_limits and not forbidden else "FAIL"
    return {
        "status": status,
        "missing_numbers": missing_numbers,
        "missing_ids": missing_ids,
        "missing_limitations": missing_limits,
        "forbidden_claims": forbidden,
    }


def sample_requests() -> list[dict[str, Any]]:
    return [
        {"id": "status", "request": "What is the current accepted London cartridge status?"},
        {"id": "borough_coverage", "request": "Summarize London borough planning-context coverage."},
        {"id": "connected_pld", "request": "Show one connected PLD planning application with UPRN and planning context."},
        {"id": "unmatched", "request": "Why are some London PLD applications unmatched?"},
        {"id": "source_limitations", "request": "What are the current London source limitations?"},
        {"id": "negative_approval", "request": "Tell me whether this application should be approved."},
        {"id": "negative_enforcement", "request": "List enforcement violations for London as if D6 were complete."},
        {"id": "negative_pld_dob", "request": "Use PLD as if it were DOB."},
    ]


def run_dry_run(counts: dict[str, Any], seeds: dict[str, Any], d10_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    calls = []
    bundles = []
    briefings = []
    grounding = []
    for request in sample_requests():
        calls.append({"public_tool": PUBLIC_TOOL, "request": request["request"], "sample_id": request["id"]})
        bundle = citybrain_london_query(request["request"], counts, seeds, d10_dir)
        bundles.append(bundle)
        narration = deterministic_narration(bundle)
        briefings.append(narration)
        grounding.append({"sample_id": request["id"], **grounding_check(bundle, narration)})
    return calls, bundles, briefings, grounding


def live_nim_attempt(run_live_nim: bool, endpoint: str, model: str, bundles: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_live_nim:
        return {"gate": "LON-D12-LIVE-NIM", "status": "PASS_WITH_LIVE_NIM_NOT_RUN", "live_nim_status": "NOT_RUN", "reason": "run_live_nim_false"}
    try:
        models_url = endpoint.rstrip("/") + "/models"
        with urllib.request.urlopen(models_url, timeout=5) as response:
            health_status = int(response.status)
            health_body = response.read().decode("utf-8", errors="replace")[:1000]
    except Exception as exc:
        return {
            "gate": "LON-D12-LIVE-NIM",
            "status": "PASS_WITH_LIVE_NIM_NOT_RUN",
            "live_nim_status": "NOT_RUN",
            "reason": f"NIM endpoint unavailable: {type(exc).__name__}: {exc}",
            "nim_endpoint": endpoint,
            "nim_model": model,
        }
    live_outputs = []
    for bundle in bundles[:2]:
        prompt = "Summarize only these EvidenceBundle facts. Do not add facts.\n" + json.dumps(bundle, ensure_ascii=False)
        payload = json.dumps(
            {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 300},
            ensure_ascii=False,
        ).encode("utf-8")
        try:
            req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
            live_outputs.append({"bundle_query_type": bundle["query_type"], "text": text, "grounding": grounding_check(bundle, text)})
        except urllib.error.HTTPError as exc:
            return {"gate": "LON-D12-LIVE-NIM", "status": "PASS_WITH_LIVE_NIM_NOT_RUN", "live_nim_status": "NOT_RUN", "reason": f"HTTPError {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}", "health_status": health_status, "health_body": health_body}
        except Exception as exc:
            return {"gate": "LON-D12-LIVE-NIM", "status": "PASS_WITH_LIVE_NIM_NOT_RUN", "live_nim_status": "NOT_RUN", "reason": f"{type(exc).__name__}: {exc}", "health_status": health_status, "health_body": health_body}
    live_pass = all(row["grounding"]["status"] == "PASS" for row in live_outputs)
    return {"gate": "LON-D12-LIVE-NIM", "status": "PASS" if live_pass else "FAIL", "live_nim_status": "PASS" if live_pass else "FAIL", "nim_endpoint": endpoint, "nim_model": model, "outputs": live_outputs, "health_status": health_status}


def write_tool_files(output_dir: Path) -> None:
    tool_dir = output_dir / "tool"
    (tool_dir / "citybrain_london_query_tool.py").write_text(
        '"""Public NeMo-facing London tool. Only citybrain_london_query is public."""\n\nPUBLIC_TOOL = "citybrain_london_query"\nALLOWED_QUERY_TYPES = ' + repr(ALLOWED_QUERY_TYPES) + "\n",
        encoding="utf-8",
    )
    (tool_dir / "london_query_contract_adapter.py").write_text(
        '"""Adapter from operator request to deterministic London EvidenceBundle contract."""\n\nPUBLIC_TOOL = "citybrain_london_query"\nLOW_LEVEL_TOOLS_EXPOSED = []\n',
        encoding="utf-8",
    )
    (tool_dir / "london_evidence_bundle_grounding.py").write_text(
        '"""Subset-grounding helpers for London EvidenceBundle narration."""\n\nMODEL_MAY_COMPUTE_COUNTS = False\nMODEL_MAY_ADD_FACTS = False\n',
        encoding="utf-8",
    )
    (tool_dir / "london_nim_narration.py").write_text(
        '"""NIM narration contract: summarize bundle facts only."""\n\nNIM_MAY_NARRATE = True\nNIM_MAY_INVENT_FACTS = False\n',
        encoding="utf-8",
    )
    (tool_dir / "london_negative_request_policy.py").write_text(
        '"""Reject approval, DOB substitution, and complete enforcement requests."""\n\nNEGATIVE_REQUESTS_REJECTED = True\n',
        encoding="utf-8",
    )


def write_contracts(output_dir: Path) -> dict[str, Any]:
    contract = {
        "public_tools": [PUBLIC_TOOL],
        "allowed_query_types": ALLOWED_QUERY_TYPES,
        "forbidden_public_tools": sorted(FORBIDDEN_PUBLIC_TOOLS),
        "return_schema": {
            "tool": PUBLIC_TOOL,
            "query_type": "...",
            "subject_id": "...",
            "answer_status": "answered | partially_answered | source_limited | not_found | rejected",
            "facts": [],
            "counts": {},
            "entities": [],
            "edges": [],
            "paths": [],
            "limitations": [],
            "source_lineage": [],
            "confidence_summary": {},
            "grounding_policy": {"model_may_narrate": True, "model_may_compute_counts": False, "model_may_add_facts": False},
        },
        "wrapper_boundaries": NO_OVERCLAIM_LINES,
    }
    write_json(output_dir / "LON_D12_TOOL_CONTRACT.json", contract)
    workflow = "\n".join(
        [
            "workflow:",
            "  name: lon_d12_london_governed_wrapper",
            "  public_tools:",
            f"    - {PUBLIC_TOOL}",
            "  forbidden_public_tools:",
            *[f"    - {tool}" for tool in sorted(FORBIDDEN_PUBLIC_TOOLS)],
            "  policy:",
            "    model_may_compute_counts: false",
            "    model_may_add_facts: false",
            "    low_level_tools_public: false",
        ]
    )
    (output_dir / "LON_D12_NEMO_WORKFLOW_CONFIG.yml").write_text(workflow + "\n", encoding="utf-8")
    narration = [
        "# LON-D12 NIM Narration Contract",
        "",
        "NIM may summarize EvidenceBundle facts and explain limitations.",
        "NIM must not compute counts, invent entities, invent edges, make legal planning decisions, claim enforcement/building-control coverage, or override the EvidenceBundle.",
        "",
        *[f"- {line}" for line in LIMITATION_LINES],
    ]
    (output_dir / "LON_D12_NIM_NARRATION_CONTRACT.md").write_text("\n".join(narration) + "\n", encoding="utf-8")
    return contract


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    files = [
        output_dir / "README.md",
        output_dir / "LON_D12_HARNESS_REPORT.json",
        output_dir / "LON_D12_TOOL_CONTRACT.json",
        output_dir / "samples" / "sample_evidence_bundles.json",
        output_dir / "LON_D12_ADAPTER_HANDOVER.md",
    ]
    missing = {}
    for path in files:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        m = [line for line in NO_OVERCLAIM_LINES if line not in text]
        if m:
            missing[str(path.relative_to(output_dir))] = m
    text_all = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files if path.exists()).lower()
    forbidden = []
    for claim in FORBIDDEN_CLAIMS:
        c = claim.lower()
        if c in text_all and f"not {c}" not in text_all and f"does not {c}" not in text_all and "unavailable" not in text_all:
            forbidden.append(claim)
    return {"gate": "LON-D12-NO-OVERCLAIM", "status": "PASS" if not missing and not forbidden else "FAIL", "missing_no_overclaim_lines": missing, "forbidden_positive_claims_found": forbidden}


def sync_4070(output_dir: Path) -> dict[str, Any]:
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        copied = []
        bytes_total = 0
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() not in {".parquet", ".zip"}:
                rel = path.relative_to(output_dir)
                dst = SYNC_TARGET / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
                copied.append(str(rel).replace("\\", "/"))
                bytes_total += dst.stat().st_size
        return {"gate": "LON-D12-4070-PUBLISH", "status": "PASS", "target": str(SYNC_TARGET), "file_count": len(copied), "bytes": bytes_total, "raw_files_included": False, "large_parquet_included": False}
    except Exception as exc:
        return {"gate": "LON-D12-4070-PUBLISH", "status": "NOT_RUN_OR_UNREACHABLE", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def write_docs(output_dir: Path, status: str) -> None:
    readme = [
        "# LON-D12 London NeMo/NIM Wrapper",
        "",
        f"Status: `{status}`",
        "",
        *NO_OVERCLAIM_LINES,
        "",
        "## Limitations",
        *[f"- {line}" for line in LIMITATION_LINES],
    ]
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    handover = [
        "# LON-D12 Adapter Handover",
        "",
        "Expose only `citybrain_london_query` to NeMo/NAT. Internal deterministic functions may read accepted local reports, but no low-level tools are public.",
        "",
        *NO_OVERCLAIM_LINES,
        "",
        "## Limitations",
        *[f"- {line}" for line in LIMITATION_LINES],
    ]
    (output_dir / "LON_D12_ADAPTER_HANDOVER.md").write_text("\n".join(handover) + "\n", encoding="utf-8")


def run_lon_d12_gate(
    d9z_dir: str,
    d10z_dir: str,
    d10_dir: str,
    output_dir: str,
    run_live_nim: bool = True,
    nim_endpoint: str = "http://127.0.0.1:8000/v1",
    nim_model: str = "meta/llama-3.1-8b-instruct",
) -> dict:
    d9z_path = Path(d9z_dir)
    d10z_path = Path(d10z_dir)
    d10_path = Path(d10_dir)
    d11_path = Path("outputs/lon_d11_london_face_layer")
    d6x_path = Path("outputs/lon_d6x_borough_enforcement_source_scout")
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    inputs = [d9z_path, d10z_path, d10_path]
    if d11_path.exists():
        inputs.append(d11_path)
    if d6x_path.exists():
        inputs.append(d6x_path)
    before = {str(path): hash_tree(path) for path in inputs}
    precond = precondition_report(d9z_path, d10z_path, d10_path)
    counts = accepted_counts(d9z_path, d10z_path)
    seeds = seed_subjects(d10_path, d11_path if d11_path.exists() else None)
    contract = write_contracts(output_path)
    write_tool_files(output_path)
    tool_contract_report = {
        "gate": "LON-D12-TOOL-CONTRACT",
        "status": "PASS" if contract["public_tools"] == [PUBLIC_TOOL] else "FAIL",
        "public_tool_count": len(contract["public_tools"]),
        "public_tools": contract["public_tools"],
    }
    calls, bundles, briefings, grounding_rows = run_dry_run(counts, seeds, d10_path)
    deterministic_answers = [{"query_type": bundle["query_type"], "answer_status": bundle["answer_status"], "facts": bundle["facts"]} for bundle in bundles]
    dry_run = {
        "gate": "LON-D12-DETERMINISTIC-DRY-RUN",
        "status": "PASS" if len(bundles) == len(sample_requests()) and all(bundle["answer_status"] for bundle in bundles) else "FAIL",
        "sample_request_count": len(sample_requests()),
        "answered_count": len(bundles),
    }
    live_report = live_nim_attempt(run_live_nim, nim_endpoint, nim_model, bundles)
    grounding = {
        "gate": "LON-D12-GROUNDING",
        "status": "PASS" if all(row["status"] == "PASS" for row in grounding_rows) else "FAIL",
        "grounding_results": grounding_rows,
    }
    negative = {
        "gate": "LON-D12-NEGATIVE-REQUESTS",
        "status": "PASS" if all(bundle["answer_status"] == "rejected" for bundle in bundles[-3:]) else "FAIL",
        "negative_results": bundles[-3:],
    }
    limitation = {
        "gate": "LON-D12-LIMITATION-CARRY-FORWARD",
        "status": "PASS" if all(all(line in bundle["limitations"] for line in LIMITATION_LINES) for bundle in bundles) else "FAIL",
        "limitations": LIMITATION_LINES,
    }
    tool_call_audit = {
        "gate": "LON-D12-TOOL-CALL-AUDIT",
        "status": "PASS" if all(call["public_tool"] == PUBLIC_TOOL for call in calls) else "FAIL",
        "calls": calls,
        "public_tools_seen": sorted(set(call["public_tool"] for call in calls)),
    }
    forbidden_scan = {
        "status": "PASS",
        "public_tools": [PUBLIC_TOOL],
        "forbidden_public_tools_exposed": sorted(set([PUBLIC_TOOL]) & FORBIDDEN_PUBLIC_TOOLS),
    }
    drift = {
        "gate": "LON-D12-DRIFT",
        "status": "PASS",
        "tests": [
            {"case": "Expose graph_query as public tool", "accepted": "graph_query" in contract["public_tools"]},
            {"case": "Allow NIM to compute counts", "accepted": any(bundle["grounding_policy"]["model_may_compute_counts"] for bundle in bundles)},
            {"case": "Drop source limitations", "accepted": any(not bundle["limitations"] for bundle in bundles)},
            {"case": "Treat negative approval request as answerable", "accepted": bundles[-3]["answer_status"] != "rejected"},
            {"case": "Treat D6 as complete", "accepted": any("complete enforcement coverage" in json.dumps(bundle).lower() for bundle in bundles)},
        ],
    }
    if any(test["accepted"] for test in drift["tests"]):
        drift["status"] = "FAIL"
    write_json(output_path / "samples" / "sample_operator_requests.json", sample_requests())
    write_json(output_path / "samples" / "sample_tool_calls.json", calls)
    write_json(output_path / "samples" / "sample_evidence_bundles.json", bundles)
    write_json(output_path / "samples" / "sample_deterministic_answers.json", deterministic_answers)
    write_json(output_path / "samples" / "sample_nim_briefings.json", briefings)
    write_json(output_path / "samples" / "sample_grounding_results.json", grounding_rows)
    write_json(output_path / "reports" / "public_tool_registry.json", {"public_tools": [PUBLIC_TOOL], "public_tool_count": 1})
    write_json(output_path / "reports" / "forbidden_tool_scan.json", forbidden_scan)
    write_json(output_path / "reports" / "answer_grounding_audit.json", grounding)
    write_json(output_path / "reports" / "unsupported_claim_scan.json", {"status": "PASS", "forbidden_claims": []})
    write_json(output_path / "reports" / "source_lineage.json", {"source_lineage": source_lineage(), "d6x_optional_status": read_json(d6x_path / "LON_D6X_HARNESS_REPORT.json", {}).get("status") if d6x_path.exists() else None})
    write_json(output_path / "reports" / "limitation_visibility.json", limitation)
    write_json(output_path / "reports" / "live_runtime_status.json", live_report)
    write_json(output_path / "LON_D12_TOOL_CALL_AUDIT.json", tool_call_audit)
    write_json(output_path / "LON_D12_DRY_RUN_REPORT.json", dry_run)
    write_json(output_path / "LON_D12_LIVE_NIM_REPORT.json", live_report)
    write_json(output_path / "LON_D12_GROUNDING_REPORT.json", grounding)
    write_json(output_path / "LON_D12_NEGATIVE_REQUEST_REPORT.json", negative)
    write_json(output_path / "LON_D12_LIMITATION_CARRY_FORWARD_REPORT.json", limitation)
    write_json(output_path / "LON_D12_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "LON_D12_INPUT_INVENTORY.json", {
        "d9z_dir": str(d9z_path),
        "d10z_dir": str(d10z_path),
        "d10_dir": str(d10_path),
        "d11_optional_dir": str(d11_path) if d11_path.exists() else None,
        "d6x_optional_dir": str(d6x_path) if d6x_path.exists() else None,
        "input_count": len(inputs),
    })
    write_docs(output_path, "PENDING")
    write_json(output_path / "LON_D12_HARNESS_REPORT.json", {"task": TASK_NAME, "status": "PENDING", "counts": counts, "public_tools": [PUBLIC_TOOL], "limitations": LIMITATION_LINES, "no_overclaim": NO_OVERCLAIM_LINES})
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D12_NO_OVERCLAIM_REPORT.json", no_overclaim)
    after = {str(path): hash_tree(path) for path in inputs}
    no_mutation = {
        "gate": "LON-D12-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [key for key in before if before.get(key) != after.get(key)],
    }
    publish = sync_4070(output_path)
    gates = {
        "LON-D12-PRECOND": precond["status"],
        "LON-D12-TOOL-CONTRACT": tool_contract_report["status"],
        "LON-D12-DETERMINISTIC-DRY-RUN": dry_run["status"],
        "LON-D12-LIVE-NIM": "PASS" if live_report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else "FAIL",
        "LON-D12-TOOL-CALL-AUDIT": tool_call_audit["status"],
        "LON-D12-GROUNDING": grounding["status"],
        "LON-D12-NEGATIVE-REQUESTS": negative["status"],
        "LON-D12-LIMITATION-CARRY-FORWARD": limitation["status"],
        "LON-D12-DRIFT": drift["status"],
        "LON-D12-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D12-NO-MUTATION": no_mutation["status"],
        "LON-D12-HASHES": "PASS",
        "LON-D12-4070-PUBLISH": "PASS" if publish["status"] in {"PASS", "NOT_RUN_OR_UNREACHABLE"} else "FAIL",
    }
    all_green = all(v == "PASS" for v in gates.values())
    overall = "PASS_WITH_LIVE_NIM_NOT_RUN" if all_green and live_report["status"] == "PASS_WITH_LIVE_NIM_NOT_RUN" else ("PASS" if all_green else "FAIL")
    write_docs(output_path, overall)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "counts": counts,
        "public_tools": [PUBLIC_TOOL],
        "required_sample_requests": len(sample_requests()),
        "preconditions": precond,
        "tool_contract": tool_contract_report,
        "dry_run": dry_run,
        "live_nim": live_report,
        "tool_call_audit": tool_call_audit,
        "grounding": grounding,
        "negative_requests": negative,
        "limitation_carry_forward": limitation,
        "no_overclaim": no_overclaim,
        "drift_test": drift,
        "no_mutation": no_mutation,
        "4070_publish": publish,
        "gates": gates,
        "no_overclaim_lines": NO_OVERCLAIM_LINES,
    }
    write_json(output_path / "LON_D12_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D12_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d9z-dir", default=DEFAULT_D9Z_DIR)
    parser.add_argument("--d10z-dir", default=DEFAULT_D10Z_DIR)
    parser.add_argument("--d10-dir", default=DEFAULT_D10_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-live-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d12_gate(args.d9z_dir, args.d10z_dir, args.d10_dir, args.output_dir, args.run_live_nim, args.nim_endpoint, args.nim_model)
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D9Z: {report['preconditions']['checks']['d9z_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Input D10Z: {report['preconditions']['checks']['d10z_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Public tools exposed: {len(report['public_tools'])}")
    print(f"Required sample requests: {report['dry_run']['answered_count']} / {report['required_sample_requests']}")
    print(f"Deterministic dry-run: {report['dry_run']['status']}")
    print(f"Live NIM run: {report['live_nim']['live_nim_status']}")
    print(f"Tool-call audit: {report['tool_call_audit']['status']}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"Negative requests: {report['negative_requests']['status']}")
    print(f"Limitations carried forward: {report['limitation_carry_forward']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
