"""
Canonical NYC DOB complaint category taxonomy.

This module is intentionally free of hero-cascade and district-scope constants.
Adapters and query layers should import DOB complaint category/type/severity
mapping from here instead of from legacy fixture builders.
"""

from __future__ import annotations

from txr_citybrain_schema_v1 import EventCategory, EventSeverity


DOB_COMPLAINT_CATEGORY_MAP = {
    "01": {
        "description": "Accident - Construction/Plumbing",
        "category": EventCategory.incident,
        "type": "construction_accident_complaint",
        "severity": EventSeverity.critical,
    },
    "05": {
        "description": "Permit - None (Building/PA/Demo etc.)",
        "category": EventCategory.incident,
        "type": "unpermitted_work_complaint",
        "severity": EventSeverity.high,
    },
    "1G": {
        "description": "Stalled Construction Site",
        "category": EventCategory.incident,
        "type": "stalled_construction_site_complaint",
        "severity": EventSeverity.medium,
    },
    "23": {
        "description": "Sidewalk Shed/Supported Scaffold/Inadequate/Defect/NONE/NO PMT/NO CERT",
        "category": EventCategory.incident,
        "type": "scaffold_safety_complaint",
        "severity": EventSeverity.high,
    },
    "3A": {
        "description": "Unlicensed/ILLEGAL/Improper Electrical Work in Progress",
        "category": EventCategory.incident,
        "type": "illegal_electrical_work_complaint",
        "severity": EventSeverity.high,
    },
    "5G": {
        "description": "Unlicensed/Illegal/Improper Work In-Progress",
        "category": EventCategory.incident,
        "type": "illegal_work_in_progress_complaint",
        "severity": EventSeverity.high,
    },
    "5H": {
        "description": "Illegal Activity",
        "category": EventCategory.incident,
        "type": "illegal_activity_complaint",
        "severity": EventSeverity.medium,
    },
    "76": {
        "description": "Unlicensed/Illegal/Improper Plumbing Work In-Progress",
        "category": EventCategory.incident,
        "type": "illegal_plumbing_work_complaint",
        "severity": EventSeverity.high,
    },
    "83": {
        "description": "Construction: Contrary/Beyond Approved Plans/Permits",
        "category": EventCategory.incident,
        "type": "work_contrary_to_permit_complaint",
        "severity": EventSeverity.high,
    },
    "86": {
        "description": "Work Contrary to Stop Work Order",
        "category": EventCategory.incident,
        "type": "stop_work_order_violation_complaint",
        "severity": EventSeverity.critical,
    },
    "8A": {
        "description": "Construction Safety Compliance (CSC) Action",
        "category": EventCategory.incident,
        "type": "construction_safety_compliance_complaint",
        "severity": EventSeverity.high,
    },
    "90": {
        "description": "Unlicensed/Illegal Activity",
        "category": EventCategory.incident,
        "type": "unlicensed_illegal_activity_complaint",
        "severity": EventSeverity.high,
    },
    "91": {
        "description": "Site Conditions Endangering Workers",
        "category": EventCategory.incident,
        "type": "site_conditions_endangering_workers",
        "severity": EventSeverity.critical,
    },
    "96": {
        "description": "Unlicensed Boiler, Electrical, Plumbing or Sign Work Completed",
        "category": EventCategory.incident,
        "type": "unlicensed_completed_work_complaint",
        "severity": EventSeverity.medium,
    },
}


def _normalize_code(code: object) -> str:
    text = str(code or "").strip()
    if not text:
        return ""
    try:
        if "." in text and float(text).is_integer():
            return str(int(float(text)))
    except ValueError:
        pass
    return text.upper()


def map_dob_complaint(code: object) -> dict[str, object]:
    normalized = _normalize_code(code)
    return DOB_COMPLAINT_CATEGORY_MAP.get(
        normalized,
        {
            "description": None,
            "category": EventCategory.incident,
            "type": "construction_complaint",
            "severity": EventSeverity.medium,
        },
    )
