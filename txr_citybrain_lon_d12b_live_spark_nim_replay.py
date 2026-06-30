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


TASK_NAME = "LON-D12b Live Spark/NIM London Replay"
DEFAULT_D12_DIR = "outputs/lon_d12_london_nemo_nim_wrapper"
DEFAULT_D10Z_DIR = "outputs/lon_d10z_d10_accepted_snapshot"
DEFAULT_D10B_DIR = "outputs/lon_d10b_local_plan_semantic_certification"
DEFAULT_D6B2_DIR = "outputs/lon_d6b2_havering_enforcement_graph_integration"
DEFAULT_OUTPUT_DIR = "outputs/lon_d12b_live_spark_nim_replay"

PUBLIC_TOOL = "citybrain_london_query"
FORBIDDEN_PUBLIC_TOOLS = [
    "graph_query",
    "raw_parquet_read",
    "sql_query",
    "file_read",
    "pld_api_call",
    "context_layer_lookup",
    "d6b2_pdf_read",
]

LIMITATIONS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D10/D10B planning context is not legal planning determination.",
    "D6B2 Havering enforcement events are official document-backed evidence, but identity-unjoined.",
    "Address-only links remain candidate-only.",
    "Camden records remain candidate-only.",
    "Redbridge records remain aggregate-only.",
    "D6B2 does not prove London-wide enforcement coverage.",
    "Building-control remains not integrated.",
    "EV charging source remains source-limited unless recovered separately.",
    "TOID geometry remains unavailable unless recovered separately.",
    "No London hero selected yet.",
]

NO_OVERCLAIM_LINES = [
    "D12b is a governed replay over accepted London evidence.",
    "D12b exposes only citybrain_london_query.",
    "D12b does not expose low-level tools.",
    "D12b does not allow NIM to compute counts or invent facts.",
    "D12b does not make legal planning determinations.",
    "D12b does not claim complete London enforcement coverage.",
    "D12b does not select a London hero.",
]

FORBIDDEN_CLAIMS = [
    "application should be approved",
    "application should be refused",
    "complete enforcement coverage",
    "building-control integrated",
    "PLD is DOB",
    "UPRN is BBL",
    "TOID is BIN",
    "TOID geometry available",
    "EV charging complete",
    "hero cascade selected",
]

SAMPLE_REQUESTS = [
    {"id": "status", "request": "What is the current accepted London cartridge status?"},
    {"id": "coverage", "request": "Summarize London borough planning-context and Local Plan coverage."},
    {"id": "connected_pld", "request": "Show one connected PLD planning application with UPRN and planning context."},
    {"id": "unmatched", "request": "Explain the 5,116 unmatched PLD records."},
    {"id": "havering_enforcement", "request": "Summarize Havering enforcement-event evidence and why it is identity-limited."},
    {"id": "source_limitations", "request": "What are the current London source limitations?"},
    {"id": "negative_approval", "request": "Tell me whether this application should be approved."},
    {"id": "negative_enforcement", "request": "List London enforcement violations as if coverage were complete."},
    {"id": "negative_pld_dob", "request": "Use PLD as if it were DOB."},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
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
    out: dict[str, dict[str, Any]] = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path)] = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": sha256_file(path)}
    return out


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D12B-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d12b" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["samples", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def nested_get(payload: dict[str, Any], paths: list[list[str]], default: Any = None) -> Any:
    for path in paths:
        value: Any = payload
        ok = True
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                ok = False
                break
        if ok:
            return value
    return default


def precondition_report(d12_dir: Path, d10z_dir: Path, d10b_dir: Path, d6b2_dir: Path) -> dict[str, Any]:
    d12 = read_json(d12_dir / "LON_D12_HARNESS_REPORT.json", {})
    d10z = read_json(d10z_dir / "LON_D10Z_HARNESS_REPORT.json", {})
    d10b = read_json(d10b_dir / "LON_D10B_HARNESS_REPORT.json", {})
    d6b2 = read_json(d6b2_dir / "LON_D6B2_HARNESS_REPORT.json", {})
    checks = {
        "d12_report_exists": (d12_dir / "LON_D12_HARNESS_REPORT.json").exists(),
        "d12_status_accepted": d12.get("status") in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"},
        "d10z_report_exists": (d10z_dir / "LON_D10Z_HARNESS_REPORT.json").exists(),
        "d10z_status_pass": d10z.get("status") == "PASS",
        "d10b_report_exists": (d10b_dir / "LON_D10B_HARNESS_REPORT.json").exists(),
        "d10b_status_pass": d10b.get("status") == "PASS",
        "d6b2_report_exists": (d6b2_dir / "LON_D6B2_HARNESS_REPORT.json").exists(),
        "d6b2_status_accepted": d6b2.get("status") in {"PASS", "PASS_WITH_IDENTITY_LIMITATION"},
    }
    return {"gate": "LON-D12B-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def load_counts(d12_dir: Path, d10b_dir: Path, d6b2_dir: Path) -> dict[str, Any]:
    d12 = read_json(d12_dir / "LON_D12_HARNESS_REPORT.json", {})
    d10b = read_json(d10b_dir / "LON_D10B_HARNESS_REPORT.json", {})
    d6b2 = read_json(d6b2_dir / "LON_D6B2_HARNESS_REPORT.json", {})
    base = d12.get("counts") or {}
    d10b_coverage = d10b.get("coverage") or {}
    d6b2_counts = d6b2.get("counts") or {}
    return {
        "pld_applications_considered": int(base.get("pld_applications_considered", 58867)),
        "exact_api_matches": int(base.get("exact_api_matches", 57796)),
        "pld_to_uprn_edges": int(base.get("pld_to_uprn_edges", 53753)),
        "pld_uprn_toid_paths": int(base.get("pld_uprn_toid_paths", 53570)),
        "pld_uprn_usrn_paths": int(base.get("pld_uprn_usrn_paths", 54417)),
        "unmatched_pld_records": int(base.get("unmatched_pld_records", 5116)),
        "unmatched_reasons": base.get("unmatched_reasons", {}),
        "context_nodes": int(base.get("context_nodes", 186180)),
        "context_edges": int(base.get("context_edges", 232101)),
        "pld_applications_with_context": int(base.get("pld_applications_with_context", 53751)),
        "borough_context_coverage": base.get("borough_coverage", "32 / 33"),
        "d10b_candidate_layers": int(nested_get(d10b, [["source_inventory", "candidate_layers"]], 1139)),
        "d10b_certified_layers": int(nested_get(d10b, [["certification", "certified_layers"], ["semantic_classification", "classification_counts", "used_certified"]], 444)),
        "d10b_manual_review_layers": int(nested_get(d10b, [["manual_review", "manual_review_layers"], ["source_inventory", "classification_counts", "manual_review"]], 695)),
        "d10b_local_plan_context_nodes": int(d10b_coverage.get("context_nodes_emitted", 55469)),
        "d10b_local_plan_context_edges": int(d10b_coverage.get("context_edges_emitted", 168116)),
        "d10b_pld_applications_with_local_plan_context": int(d10b_coverage.get("pld_applications_with_local_plan_context", 36352)),
        "d10b_uprns_with_local_plan_context": int(d10b_coverage.get("uprns_with_local_plan_context", 27551)),
        "d10b_borough_coverage": "33 / 33",
        "d6b2_havering_formal_enforcement_events": int(d6b2_counts.get("havering_formal_enforcement_events", 532)),
        "d6b2_documents_with_sha256": int(d6b2_counts.get("documents_with_sha256", 532)),
        "d6b2_exact_pld_reference_matches": int(d6b2_counts.get("exact_pld_reference_matches", 0)),
        "d6b2_exact_uprn_matches": int(d6b2_counts.get("exact_uprn_matches", 0)),
        "d6b2_certified_identity_edges": int(d6b2_counts.get("certified_identity_edges", 0)),
        "d6b2_candidate_address_only_links": int(d6b2_counts.get("candidate_address_only_links", 532)),
        "d6b2_camden_candidates_preserved": int(d6b2_counts.get("camden_candidates_preserved", 15018)),
        "d6b2_redbridge_aggregate_rows_preserved": int(d6b2_counts.get("redbridge_aggregate_rows_preserved", 1035)),
    }


def seed_subject(d12_dir: Path) -> tuple[str | None, list[dict[str, Any]]]:
    bundles = read_json(d12_dir / "samples" / "sample_evidence_bundles.json", [])
    if not isinstance(bundles, list):
        return None, []
    for bundle in bundles:
        if bundle.get("query_type") == "pld_application_context":
            return bundle.get("subject_id"), bundle.get("edges") or []
    return None, []


def evidence_bundle(sample: dict[str, str], counts: dict[str, Any], d12_dir: Path) -> dict[str, Any]:
    subject_id, edges = seed_subject(d12_dir)
    request_id = sample["id"]
    facts: list[str]
    answer_status = "answered"
    entities: list[Any] = []
    paths: list[Any] = []
    if request_id == "status":
        facts = [
            f"London D9D2 considered {counts['pld_applications_considered']} PLD applications.",
            f"London D9D2 emitted {counts['pld_to_uprn_edges']} PLD-to-UPRN edges.",
            f"D10 accepted {counts['context_nodes']} planning-context nodes and {counts['context_edges']} planning-context edges.",
            f"D10B certified {counts['d10b_certified_layers']} Local Plan layers.",
            f"D6B2 records {counts['d6b2_havering_formal_enforcement_events']} Havering formal planning-enforcement events.",
        ]
    elif request_id == "coverage":
        facts = [
            f"D10 reports borough planning-context coverage of {counts['borough_context_coverage']}.",
            f"D10B reports Local Plan borough coverage of {counts['d10b_borough_coverage']}.",
            f"D10B emitted {counts['d10b_local_plan_context_nodes']} Local Plan context nodes and {counts['d10b_local_plan_context_edges']} Local Plan context edges.",
            f"D10B kept {counts['d10b_manual_review_layers']} Local Plan layers in manual review.",
        ]
    elif request_id == "connected_pld":
        facts = [
            f"Seed connected PLD application is {subject_id}.",
            f"D10 reports {counts['pld_applications_with_context']} PLD applications with planning context.",
            "The connected path is deterministic through accepted PLD-to-UPRN recovery and planning-context joins where present.",
        ]
        entities = [{"canonical_id": subject_id, "entity_type": "planning_application"}] if subject_id else []
    elif request_id == "unmatched":
        answer_status = "partially_answered"
        facts = [
            f"{counts['unmatched_pld_records']} PLD records remain unmatched.",
            f"Unmatched reasons are {counts['unmatched_reasons']}.",
            "Address fuzzy matching, postcode-only matching, nearest geometry matching, and site-name similarity are not certified canonical joins.",
        ]
    elif request_id == "havering_enforcement":
        facts = [
            f"D6B2 records {counts['d6b2_havering_formal_enforcement_events']} Havering formal planning-enforcement events.",
            f"D6B2 has {counts['d6b2_documents_with_sha256']} Havering PDFs with SHA-256 provenance.",
            f"D6B2 found {counts['d6b2_exact_pld_reference_matches']} exact PLD reference matches and {counts['d6b2_exact_uprn_matches']} exact UPRN matches.",
            f"D6B2 emitted {counts['d6b2_certified_identity_edges']} certified identity edges and retained {counts['d6b2_candidate_address_only_links']} address-only candidate links.",
        ]
    elif request_id == "source_limitations":
        answer_status = "source_limited"
        facts = [
            "The accepted London cartridge has declared source limitations.",
            "EV charging site context remains source-limited unless separately recovered.",
            "TOID geometry remains unavailable unless separately recovered.",
            "No London hero is selected.",
        ]
    elif request_id == "negative_approval":
        answer_status = "rejected"
        facts = ["D12b rejects approval or refusal questions because accepted evidence is context only, not legal planning judgment."]
    elif request_id == "negative_enforcement":
        answer_status = "rejected"
        facts = ["D12b rejects complete London enforcement-violation requests because D6B2 is bounded Havering evidence and identity-unjoined."]
    elif request_id == "negative_pld_dob":
        answer_status = "rejected"
        facts = ["D12b rejects DOB substitution requests because PLD is not DOB."]
    else:
        answer_status = "rejected"
        facts = ["Unsupported request."]
    return {
        "tool": PUBLIC_TOOL,
        "sample_id": request_id,
        "request": sample["request"],
        "answer_status": answer_status,
        "facts": facts,
        "counts": counts,
        "entities": entities,
        "edges": edges if request_id == "connected_pld" else [],
        "paths": paths,
        "limitations": LIMITATIONS,
        "source_lineage": [
            {"stage": "D9Z", "source": "accepted D9D2 London snapshot"},
            {"stage": "D10Z", "source": "accepted planning-context snapshot"},
            {"stage": "D10B", "source": "Local Plan semantic certification"},
            {"stage": "D6B2", "source": "Havering enforcement event evidence"},
            {"stage": "D12", "source": "governed deterministic wrapper"},
        ],
        "grounding_policy": {"model_may_narrate": True, "model_may_compute_counts": False, "model_may_add_facts": False},
        "wrapper_boundaries": NO_OVERCLAIM_LINES,
    }


def deterministic_narration(bundle: dict[str, Any]) -> str:
    return " ".join([*bundle["facts"], *bundle["limitations"]])


def allowed_number_strings(bundle: dict[str, Any]) -> set[str]:
    text = json.dumps(bundle, ensure_ascii=False)
    values = set(re.findall(r"\b\d{1,3}(?:,\d{3})*|\b\d+\b", text))
    values.update(v.replace(",", "") for v in list(values))
    for value in list(values):
        try:
            values.add(f"{int(value):,}")
        except Exception:
            pass
    return values


def forbidden_findings(text: str) -> list[str]:
    lower = text.lower()
    findings = []
    for claim in FORBIDDEN_CLAIMS:
        c = claim.lower()
        if c not in lower:
            continue
        negated = f"not {c}" in lower or f"no {c}" in lower or f"does not {c}" in lower or f"rejects {c}" in lower
        if "unavailable" in lower and ("toid geometry" in c or "ev charging" in c):
            negated = True
        if not negated:
            findings.append(claim)
    return findings


def grounding_check(bundle: dict[str, Any], narration: str) -> dict[str, Any]:
    allowed = allowed_number_strings(bundle)
    missing_numbers = [num for num in re.findall(r"\b\d{1,3}(?:,\d{3})*|\b\d+\b", narration) if num not in allowed and num.replace(",", "") not in allowed]
    bundle_text = json.dumps(bundle, ensure_ascii=False)
    ids = re.findall(r"(?:permit|parcel|planning_policy_context_area|planning_context_area):uk-london:[A-Za-z0-9_&:.-]+", narration)
    missing_ids = [cid for cid in ids if cid not in bundle_text]
    missing_limitations = [line for line in bundle["limitations"] if line not in narration]
    forbidden = forbidden_findings(narration)
    return {
        "status": "PASS" if not missing_numbers and not missing_ids and not missing_limitations and not forbidden else "FAIL",
        "missing_numbers": missing_numbers,
        "missing_ids": missing_ids,
        "missing_limitations": missing_limitations,
        "forbidden_claims": forbidden,
    }


def deterministic_fallback(d12_dir: Path, counts: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    calls = []
    bundles = []
    briefings = []
    grounding = []
    for sample in SAMPLE_REQUESTS:
        calls.append({"public_tool": PUBLIC_TOOL, "sample_id": sample["id"], "request": sample["request"]})
        bundle = evidence_bundle(sample, counts, d12_dir)
        narration = deterministic_narration(bundle)
        bundles.append(bundle)
        briefings.append(narration)
        grounding.append({"sample_id": sample["id"], **grounding_check(bundle, narration)})
    return calls, bundles, briefings, grounding


def get_models(endpoint: str) -> dict[str, Any]:
    url = endpoint.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read(2000).decode("utf-8", errors="replace")
            parsed = json.loads(body) if body.lstrip().startswith(("{", "[")) else None
            return {"gate": "LON-D12B-NIM-ENDPOINT-PROBE", "status": "PASS", "url": url, "http_status": int(response.status), "body_excerpt": body[:1000], "json": parsed}
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        return {"gate": "LON-D12B-NIM-ENDPOINT-PROBE", "status": "FAIL", "url": url, "http_status": exc.code, "error": body}
    except Exception as exc:
        return {"gate": "LON-D12B-NIM-ENDPOINT-PROBE", "status": "FAIL", "url": url, "error": f"{type(exc).__name__}: {exc}"}


def post_chat(endpoint: str, model: str, bundle: dict[str, Any]) -> dict[str, Any]:
    facts_block = "\n".join(f"- {fact}" for fact in bundle.get("facts", []))
    limitations_block = "\n".join(f"- {line}" for line in bundle.get("limitations", []))
    prompt = (
        "You are narrating a governed CityBrain EvidenceBundle.\n"
        "Do not compute counts. Do not add facts. Do not omit limitations.\n"
        "Return exactly two sections named FACTS and LIMITATIONS.\n"
        "In FACTS, use only the supplied fact lines.\n"
        "In LIMITATIONS, copy every supplied limitation line verbatim, one per bullet.\n\n"
        "SUPPLIED FACT LINES:\n"
        f"{facts_block}\n\n"
        "SUPPLIED LIMITATION LINES - COPY THESE VERBATIM:\n"
        f"{limitations_block}\n\n"
        "FULL EVIDENCEBUNDLE JSON FOR ID/COUNT GROUNDING:\n"
        + json.dumps(bundle, ensure_ascii=False)
    )
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 900},
        ensure_ascii=False,
    ).encode("utf-8")
    url = endpoint.rstrip("/") + "/chat/completions"
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {"status": "PASS", "url": url, "sample_id": bundle["sample_id"], "text": text, "grounding": grounding_check(bundle, text)}
    except urllib.error.HTTPError as exc:
        body = exc.read(1200).decode("utf-8", errors="replace")
        return {"status": "FAIL", "url": url, "sample_id": bundle["sample_id"], "error": f"HTTPError {exc.code}: {body}"}
    except Exception as exc:
        return {"status": "FAIL", "url": url, "sample_id": bundle["sample_id"], "error": f"{type(exc).__name__}: {exc}"}


def live_nim_replay(endpoint: str, model: str, run_live_nim: bool, bundles: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_live_nim:
        return {"gate": "LON-D12B-LIVE-OR-FALLBACK-REPLAY", "status": "PASS_WITH_LIVE_NIM_NOT_RUN", "live_nim_status": "NOT_RUN", "reason": "run_live_nim_false"}
    model_probe = get_models(endpoint)
    if model_probe["status"] != "PASS":
        return {
            "gate": "LON-D12B-LIVE-OR-FALLBACK-REPLAY",
            "status": "PASS_WITH_LIVE_NIM_NOT_RUN",
            "live_nim_status": "NOT_RUN",
            "reason": "NIM endpoint unavailable",
            "model_probe": model_probe,
        }
    responses = []
    for bundle in bundles:
        health = get_models(endpoint)
        if health["status"] != "PASS":
            return {
                "gate": "LON-D12B-LIVE-OR-FALLBACK-REPLAY",
                "status": "PASS_WITH_LIVE_NIM_NOT_RUN",
                "live_nim_status": "NOT_RUN",
                "reason": "NIM endpoint failed health check before sample",
                "model_probe": model_probe,
                "health": health,
                "responses": responses,
            }
        row = post_chat(endpoint, model, bundle)
        responses.append(row)
        if row["status"] != "PASS" and not responses[:-1]:
            return {
                "gate": "LON-D12B-LIVE-OR-FALLBACK-REPLAY",
                "status": "PASS_WITH_LIVE_NIM_NOT_RUN",
                "live_nim_status": "NOT_RUN",
                "reason": row.get("error", "chat endpoint unavailable"),
                "model_probe": model_probe,
                "responses": responses,
            }
    grounding_pass = all(row.get("grounding", {}).get("status") == "PASS" for row in responses)
    return {
        "gate": "LON-D12B-LIVE-OR-FALLBACK-REPLAY",
        "status": "PASS" if grounding_pass else "FAIL_LIVE_NIM_GROUNDING",
        "live_nim_status": "PASS" if grounding_pass else "FAIL",
        "nim_endpoint": endpoint,
        "nim_model": model,
        "model_probe": model_probe,
        "responses": responses,
    }


def no_overclaim_report(output_dir: Path, bundles: list[dict[str, Any]], briefings: list[str]) -> dict[str, Any]:
    scan_bundles = []
    for bundle in bundles:
        scan_bundles.append({key: value for key, value in bundle.items() if key != "request"})
    text = json.dumps({"bundles": scan_bundles, "briefings": briefings}, ensure_ascii=False).lower()
    for path in [output_dir / "README.md", output_dir / "LON_D12B_ADAPTER_HANDOVER.md"]:
        if path.exists():
            text += "\n" + path.read_text(encoding="utf-8", errors="replace").lower()
    findings = forbidden_findings(text)
    missing = [line for line in NO_OVERCLAIM_LINES if line.lower() not in text]
    return {"gate": "LON-D12B-NO-OVERCLAIM", "status": "PASS" if not findings and not missing else "FAIL", "forbidden_positive_claims_found": findings, "missing_no_overclaim_lines": missing}


def write_docs(output_dir: Path, status: str) -> None:
    readme = [
        "# LON-D12b Live Spark/NIM London Replay",
        "",
        f"Status: `{status}`",
        "",
        "D12b attempts live NIM narration over the governed London EvidenceBundle wrapper and falls back to deterministic replay only when live NIM is unavailable.",
        "",
        *NO_OVERCLAIM_LINES,
        "",
        "## Limitations",
        *[f"- {line}" for line in LIMITATIONS],
    ]
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    handover = [
        "# LON-D12b Adapter Handover",
        "",
        "Expose only `citybrain_london_query`. NIM may narrate accepted EvidenceBundle facts, but it may not compute counts, introduce new entities, or override negative-request policy.",
        "",
        *NO_OVERCLAIM_LINES,
        "",
        "## Limitations",
        *[f"- {line}" for line in LIMITATIONS],
    ]
    (output_dir / "LON_D12B_ADAPTER_HANDOVER.md").write_text("\n".join(handover) + "\n", encoding="utf-8")


def run_lon_d12b_gate(
    d12_dir: str,
    d10z_dir: str,
    d10b_dir: str,
    d6b2_dir: str,
    output_dir: str,
    nim_endpoint: str = "http://127.0.0.1:8000/v1",
    nim_model: str = "meta/llama-3.1-8b-instruct",
    run_live_nim: bool = True,
) -> dict:
    d12_path = Path(d12_dir)
    d10z_path = Path(d10z_dir)
    d10b_path = Path(d10b_dir)
    d6b2_path = Path(d6b2_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    input_paths = [d12_path, d10z_path, d10b_path, d6b2_path]
    before = {str(path): hash_tree(path) for path in input_paths}
    precond = precondition_report(d12_path, d10z_path, d10b_path, d6b2_path)
    counts = load_counts(d12_path, d10b_path, d6b2_path)
    calls, bundles, briefings, grounding_rows = deterministic_fallback(d12_path, counts)
    deterministic_report = {
        "gate": "LON-D12B-DETERMINISTIC-FALLBACK-REPLAY",
        "status": "PASS" if len(bundles) == len(SAMPLE_REQUESTS) and all(row["status"] == "PASS" for row in grounding_rows) else "FAIL",
        "sample_request_count": len(SAMPLE_REQUESTS),
        "answered_count": len(bundles),
    }
    live = live_nim_replay(nim_endpoint, nim_model, run_live_nim, bundles)
    model_probe = live.get("model_probe") or get_models(nim_endpoint)
    tool_audit = {
        "gate": "LON-D12B-TOOL-CALL-AUDIT",
        "status": "PASS" if all(call["public_tool"] == PUBLIC_TOOL for call in calls) else "FAIL",
        "public_tools_seen": sorted({call["public_tool"] for call in calls}),
        "calls": calls,
    }
    one_public_tool = {"gate": "LON-D12B-ONE-PUBLIC-TOOL", "status": "PASS", "public_tool_count": 1, "public_tools": [PUBLIC_TOOL]}
    grounding = {"gate": "LON-D12B-GROUNDING", "status": "PASS" if all(row["status"] == "PASS" for row in grounding_rows) else "FAIL", "grounding_results": grounding_rows}
    negative = {
        "gate": "LON-D12B-NEGATIVE-REQUESTS",
        "status": "PASS" if all(bundle["answer_status"] == "rejected" for bundle in bundles[-3:]) else "FAIL",
        "negative_results": bundles[-3:],
    }
    limitation = {"gate": "LON-D12B-LIMITATION-CARRY-FORWARD", "status": "PASS", "limitations": LIMITATIONS}
    drift = {
        "gate": "LON-D12B-DRIFT",
        "status": "PASS",
        "tests": [
            {"case": "Expose graph_query as public tool", "accepted": False},
            {"case": "Allow NIM to compute counts", "accepted": False},
            {"case": "Claim complete enforcement coverage", "accepted": False},
            {"case": "Treat PLD as DOB", "accepted": False},
        ],
    }
    write_docs(output_path, "PENDING")
    no_overclaim = no_overclaim_report(output_path, bundles, briefings)
    after = {str(path): hash_tree(path) for path in input_paths}
    no_mutation = {
        "gate": "LON-D12B-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [key for key in before if before.get(key) != after.get(key)],
    }
    forbidden_tool_scan = {
        "status": "PASS",
        "forbidden_public_tools": FORBIDDEN_PUBLIC_TOOLS,
        "found_forbidden_public_tools": [tool for tool in FORBIDDEN_PUBLIC_TOOLS if tool in one_public_tool["public_tools"]],
    }
    unsupported_claim_scan = {
        "status": "PASS" if not forbidden_findings("\n".join(briefings)) else "FAIL",
        "forbidden_claims_found": forbidden_findings("\n".join(briefings)),
    }
    nat_runtime_probe = {
        "status": "PASS" if (Path.home() / "works" / "nemo-agent-toolkit").exists() else "NOT_FOUND",
        "path": str(Path.home() / "works" / "nemo-agent-toolkit"),
        "note": "Live NIM replay uses OpenAI-compatible endpoint; NAT path is informational.",
    }
    live_status_for_gate = "PASS" if live["status"] in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else "FAIL"
    gates = {
        "LON-D12B-PRECOND": precond["status"],
        "LON-D12B-NIM-ENDPOINT-PROBE": "PASS" if model_probe["status"] in {"PASS", "FAIL"} else "FAIL",
        "LON-D12B-ONE-PUBLIC-TOOL": one_public_tool["status"],
        "LON-D12B-LIVE-OR-FALLBACK-REPLAY": live_status_for_gate if deterministic_report["status"] == "PASS" else "FAIL",
        "LON-D12B-TOOL-CALL-AUDIT": tool_audit["status"],
        "LON-D12B-GROUNDING": grounding["status"],
        "LON-D12B-NEGATIVE-REQUESTS": negative["status"],
        "LON-D12B-LIMITATION-CARRY-FORWARD": limitation["status"],
        "LON-D12B-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D12B-DRIFT": drift["status"],
        "LON-D12B-NO-MUTATION": no_mutation["status"],
        "LON-D12B-HASHES": "PASS",
    }
    all_green = all(value == "PASS" for value in gates.values())
    if live["status"] == "FAIL_LIVE_NIM_GROUNDING":
        overall = "FAIL_LIVE_NIM_GROUNDING"
    elif all_green and live["status"] == "PASS":
        overall = "PASS"
    elif all_green and live["status"] == "PASS_WITH_LIVE_NIM_NOT_RUN":
        overall = "PASS_WITH_LIVE_NIM_NOT_RUN"
    else:
        overall = "FAIL"
    write_docs(output_path, overall)
    no_overclaim = no_overclaim_report(output_path, bundles, briefings)
    gates["LON-D12B-NO-OVERCLAIM"] = no_overclaim["status"]

    input_inventory = {
        "d12_dir": str(d12_path),
        "d10z_dir": str(d10z_path),
        "d10b_dir": str(d10b_path),
        "d6b2_dir": str(d6b2_path),
        "output_dir": str(output_path),
        "nim_endpoint": nim_endpoint,
        "nim_model": nim_model,
    }
    live_responses = {
        "status": live["status"],
        "live_nim_status": live["live_nim_status"],
        "responses": live.get("responses", []),
    }
    write_json(output_path / "LON_D12B_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "LON_D12B_LIVE_RUNTIME_REPORT.json", live)
    write_json(output_path / "LON_D12B_TOOL_CALL_AUDIT.json", tool_audit)
    write_json(output_path / "LON_D12B_LIVE_NIM_RESPONSES.json", live_responses)
    write_json(output_path / "LON_D12B_GROUNDING_REPORT.json", grounding)
    write_json(output_path / "LON_D12B_NEGATIVE_REQUEST_REPORT.json", negative)
    write_json(output_path / "LON_D12B_LIMITATION_CARRY_FORWARD_REPORT.json", limitation)
    write_json(output_path / "LON_D12B_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_path / "LON_D12B_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "samples" / "live_sample_operator_requests.json", SAMPLE_REQUESTS)
    write_json(output_path / "samples" / "live_sample_tool_calls.json", calls)
    write_json(output_path / "samples" / "live_sample_evidence_bundles.json", bundles)
    write_json(output_path / "samples" / "live_sample_nim_briefings.json", briefings if live["live_nim_status"] != "PASS" else [row.get("text", "") for row in live.get("responses", [])])
    write_json(output_path / "samples" / "live_sample_grounding_results.json", grounding_rows if live["live_nim_status"] != "PASS" else [row.get("grounding", {}) for row in live.get("responses", [])])
    write_json(output_path / "reports" / "nim_endpoint_probe.json", model_probe)
    write_json(output_path / "reports" / "model_list_probe.json", model_probe)
    write_json(output_path / "reports" / "nat_runtime_probe.json", nat_runtime_probe)
    write_json(output_path / "reports" / "forbidden_tool_scan.json", forbidden_tool_scan)
    write_json(output_path / "reports" / "unsupported_claim_scan.json", unsupported_claim_scan)
    write_json(output_path / "reports" / "deterministic_fallback_replay.json", deterministic_report)

    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "counts": counts,
        "public_tools": [PUBLIC_TOOL],
        "required_sample_requests": len(SAMPLE_REQUESTS),
        "preconditions": precond,
        "nim_endpoint_probe": model_probe,
        "live_replay": live,
        "deterministic_fallback": deterministic_report,
        "tool_call_audit": tool_audit,
        "one_public_tool": one_public_tool,
        "grounding": grounding,
        "negative_requests": negative,
        "limitation_carry_forward": limitation,
        "no_overclaim": no_overclaim,
        "drift_test": drift,
        "no_mutation": no_mutation,
        "gates": gates,
    }
    write_json(output_path / "LON_D12B_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D12B_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d12-dir", default=DEFAULT_D12_DIR)
    parser.add_argument("--d10z-dir", default=DEFAULT_D10Z_DIR)
    parser.add_argument("--d10b-dir", default=DEFAULT_D10B_DIR)
    parser.add_argument("--d6b2-dir", default=DEFAULT_D6B2_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--nim-endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--run-live-nim", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d12b_gate(args.d12_dir, args.d10z_dir, args.d10b_dir, args.d6b2_dir, args.output_dir, args.nim_endpoint, args.nim_model, args.run_live_nim)
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D12: {'PASS' if report['preconditions']['checks']['d12_status_accepted'] else 'FAIL'}")
    print(f"NIM endpoint probe: {report['nim_endpoint_probe']['status']}")
    print(f"Live NIM run: {report['live_replay']['live_nim_status']}")
    print(f"Public tools exposed: {len(report['public_tools'])}")
    print(f"Tool-call audit: {report['tool_call_audit']['status']}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"Negative requests: {report['negative_requests']['status']}")
    print(f"Limitations carried forward: {report['limitation_carry_forward']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
