"""
A5 narration grounding gate.

Checks that a NIM/NeMo narration only uses identifiers, numbers, dates, and
party-like names present in the deterministic A5-D1 evidence record.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BOUNDARY_STATEMENT = (
    "DOB enrichment is built from the current harvested DOB subset, capped and "
    "deduped across sample/chunk files, not full NYC DOB history. Counts are subset counts."
)

DOMAIN_NAME_ALLOWLIST = {
    "A5",
    "A5-D1",
    "Action Core",
    "Applicant",
    "Applicants",
    "BBL",
    "BIN",
    "Contractor",
    "DOB",
    "DOB NOW",
    "Evidence",
    "Evidence Boundary",
    "Filing",
    "Filing Representative",
    "Filing Representatives",
    "Filing Representatives",
    "NeMo",
    "NIM",
    "NYC",
    "NYC DOB",
    "Operational Briefing",
    "Operational briefing",
    "Parcel",
    "Permit",
    "Responsible",
    "Review",
    "Review Next",
    "Source",
    "TXR City Brain",
    "What Changed",
    "What Is Happening",
    "Who's responsible",
}


def read_text_or_json_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        for key in ("narrated_briefing", "text", "narration"):
            if isinstance(payload, dict) and isinstance(payload.get(key), str):
                return payload[key]
        if isinstance(payload, dict) and isinstance(payload.get("llm_narration"), dict):
            llm_text = payload["llm_narration"].get("text")
            if isinstance(llm_text, str):
                return llm_text
    return text


def flatten_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            values.append(str(key))
            values.extend(flatten_values(val))
    elif isinstance(value, list):
        for item in value:
            values.extend(flatten_values(item))
    elif value is None:
        return values
    else:
        values.append(str(value))
    return values


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def extract_strict_tokens(text: str) -> set[str]:
    patterns = [
        r"\b[A-Za-z]+:[A-Za-z0-9_:\-.]+\b",
        r"\b[A-Z]{1,4}-\d{3,}\b",
        r"\b[a-f0-9]{12}\b",
        r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?\b",
        r"\b\d+\.\d+\b",
        r"\b\d{1,10}\b",
    ]
    tokens: set[str] = set()
    for pattern in patterns:
        tokens.update(re.findall(pattern, text))
    return tokens


def evidence_party_names(evidence: Any) -> set[str]:
    names: set[str] = set()
    text = "\n".join(flatten_values(evidence))
    for match in re.finditer(r"Responsible party evidence - [^:]+:\s+(.+?)\s+\(", text):
        names.add(match.group(1).strip())
    for match in re.finditer(r"Responsible party evidence:\s+[^ ]+\s+via\s+[^ ]+\s+edge\s+to\s+(.+?)\s+\(", text):
        names.add(match.group(1).strip())
    for key in ("name",):
        for match in re.finditer(rf'"{key}"\s*:\s*"([^"]+)"', json.dumps(evidence, ensure_ascii=False)):
            names.add(match.group(1).strip())
    return {name for name in names if name}


def extract_party_like_names(narration: str) -> set[str]:
    candidates: set[str] = set()
    for line in narration.splitlines():
        clean = line.strip(" -*\t:+")
        if not clean:
            continue
        if len(clean) > 90 or clean.endswith("."):
            continue
        before_paren = clean.split("(", 1)[0].strip(" -*\t:+")
        before_paren = re.sub(
            r"^(Contractor|Applicant|Applicants|Filing Representative|Filing Representatives):\s+",
            "",
            before_paren,
            flags=re.I,
        )
        if before_paren:
            candidates.add(before_paren)
    for match in re.finditer(
        r"\b(?:[A-Z][A-Za-z&.'-]+|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z&.'-]+|[A-Z]{2,}|&)){1,6}\b",
        narration,
    ):
        candidates.add(match.group(0).strip())
    filtered = set()
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if not candidate or candidate in DOMAIN_NAME_ALLOWLIST:
            continue
        if candidate.endswith(" Representative"):
            continue
        if candidate.startswith(("What ", "Review ", "Evidence ", "Responsible ")):
            continue
        if len(candidate) < 4:
            continue
        filtered.add(candidate)
    return filtered


def token_grounded(token: str, evidence_text: str, evidence_compact: str) -> bool:
    if normalize(token) in evidence_text:
        return True
    return compact(token) in evidence_compact


def run_grounding_gate(evidence_path: str, narration_path: str, output_path: str | None = None) -> dict[str, Any]:
    evidence_file = Path(evidence_path)
    narration_file = Path(narration_path)
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    narration = read_text_or_json_text(narration_file)
    evidence_values = flatten_values(evidence)
    evidence_text = normalize("\n".join(evidence_values))
    evidence_compact = compact("\n".join(evidence_values))
    strict_tokens = extract_strict_tokens(narration)
    missing_strict = sorted(token for token in strict_tokens if not token_grounded(token, evidence_text, evidence_compact))

    known_names = evidence_party_names(evidence)
    known_names_compact = {compact(name): name for name in known_names}
    narration_names = extract_party_like_names(narration)
    missing_names = []
    for name in sorted(narration_names):
        name_key = compact(name)
        if name_key in known_names_compact:
            continue
        if token_grounded(name, evidence_text, evidence_compact):
            continue
        missing_names.append(name)

    boundary_present = BOUNDARY_STATEMENT in narration
    report = {
        "gate_id": "A5-NARRATION-GROUNDED",
        "status": "PASS" if not missing_strict and not missing_names and boundary_present else "FAIL",
        "boundary_statement_present": boundary_present,
        "evidence_path": str(evidence_file),
        "narration_path": str(narration_file),
        "strict_tokens_checked": sorted(strict_tokens),
        "missing_strict_tokens": missing_strict,
        "party_like_names_checked": sorted(narration_names),
        "missing_party_like_names": missing_names,
        "known_evidence_party_names": sorted(known_names),
        "rule": "Every extracted identifier/date/number/name in the narration must appear in the deterministic evidence JSON.",
    }
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run A5 narration grounding gate.")
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--narration", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    report = run_grounding_gate(args.evidence_json, args.narration, args.output)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
