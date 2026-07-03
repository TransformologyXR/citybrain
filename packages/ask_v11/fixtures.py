"""Local ASK v1.1 fixtures for P2 template execution.

These records are not production/live data. They exist so G5 can prove
route-whitelisted template execution without external services.
"""

from __future__ import annotations

from .packets import SourceRef


FIXTURE_ALIASES: dict[str, str] = {
    "wood lane": "asset:ev:wood-lane",
    "wood lane charger": "asset:ev:wood-lane",
    "demo building": "building:demo:001",
    "business bay": "community:demo:business-bay",
    "wood lane works": "source:works:wood-lane-001",
    "pending queue": "queue:patch:pending",
}


ENTITY_FIXTURES: dict[str, dict] = {
    "asset:ev:wood-lane": {
        "entity_ref": "asset:ev:wood-lane",
        "label": "Wood Lane EV charging access asset",
        "entity_type": "mobility_access_asset",
        "knowns": [
            "Retained fixture identifies an EV charging access asset at Wood Lane.",
            "A nearby works source record exists in the demo fixture.",
        ],
        "unknowns": [
            "Current live charger occupancy is not ingested.",
            "Confirmed access blockage is not proven by proximity alone.",
        ],
    },
    "building:demo:001": {
        "entity_ref": "building:demo:001",
        "label": "Demo building 001",
        "entity_type": "building",
        "knowns": [
            "Retained fixture identifies a demo building record.",
            "The record is suitable for profile-style ASK tests only.",
        ],
        "unknowns": [
            "Certified legal status is not inferred from this retained fixture.",
        ],
    },
    "community:demo:business-bay": {
        "entity_ref": "community:demo:business-bay",
        "label": "Business Bay demo community",
        "entity_type": "community",
        "knowns": [
            "Retained fixture identifies a demo community context.",
        ],
        "unknowns": [
            "Live service status and official actions are not executed.",
        ],
    },
}


SOURCE_RECORD_FIXTURES: dict[str, dict] = {
    "source:works:wood-lane-001": {
        "source_record_ref": "source:works:wood-lane-001",
        "title": "Wood Lane planned works record",
        "summary": "Demo retained works record near the Wood Lane EV asset.",
        "source_owner": "Demo works register",
        "limitations": [
            "The record does not prove live access blockage.",
            "The record does not prove current charger availability.",
        ],
    }
}


SUBJECT_FACTS: dict[str, list[dict]] = {
    "asset:ev:wood-lane": [
        {
            "fact_id": "wood-lane-retained-asset",
            "text": "The retained fixture has an EV access asset for Wood Lane.",
            "source_ref": "fixture:entity_profile",
        },
        {
            "fact_id": "wood-lane-nearby-works",
            "text": "A retained works source record is nearby, but proximity is not confirmed impact.",
            "source_ref": "fixture:source_records",
        },
    ],
    "building:demo:001": [
        {
            "fact_id": "demo-building-retained-profile",
            "text": "The retained fixture has a demo building profile.",
            "source_ref": "fixture:entity_profile",
        }
    ],
    "community:demo:business-bay": [
        {
            "fact_id": "business-bay-retained-community",
            "text": "The retained fixture has a demo community context.",
            "source_ref": "fixture:entity_profile",
        }
    ],
}


PATCH_QUEUE_ROWS: list[dict] = [
    {
        "queue_item_ref": "queue:item:001",
        "queue_ref": "queue:patch:pending",
        "status": "pending",
        "title": "Review Wood Lane access-impact wording",
        "not_executed": "review-state mutation",
    },
    {
        "queue_item_ref": "queue:item:002",
        "queue_ref": "queue:patch:pending",
        "status": "pending",
        "title": "Verify source-owner label before claim",
        "not_executed": "source-owner mutation",
    },
]


INTERNAL_SOURCE_REFS: dict[str, SourceRef] = {
    "board_meta": SourceRef(
        source_id="internal:ask_v11_board_meta",
        source_type="internal_contract_note",
        title="ASK v1.1 board capability contract note",
        owner="ASK v1.1 contract",
        claim_boundary="Static product capability evidence only.",
    ),
    "external_context": SourceRef(
        source_id="internal:ask_v11_external_context_registry",
        source_type="internal_registry_note",
        title="ASK v1.1 external context registry note",
        owner="ASK v1.1 Concept-Binding Registry",
        claim_boundary="Known external source need; no live source executed.",
    ),
}


def fixture_aliases() -> list[str]:
    return sorted(FIXTURE_ALIASES.values())
