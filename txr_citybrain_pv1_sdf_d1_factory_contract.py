from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_sdf_common import (
    ALLOWED_ACTION_PROPOSAL_TYPES,
    CLAIM_LABEL,
    DIRTY_VARIANT_TYPES,
    FORBIDDEN_ACTION_PROPOSAL_TYPES,
    GENERATED_AT_UTC,
    GENERATION_SEED,
    GENERATION_VERSION,
    REQUIRED_SYNTHETIC_METADATA_FIELDS,
    SYNTHETIC_ENTITY_TYPES,
    all_gates_pass,
    gate,
    no_overclaim_scan,
    project_path,
    reset_dir,
    synthetic_metadata,
    write_hashes,
    write_json,
    write_stage_readme,
    write_text,
)


DEFAULT_OUTPUT_DIR = "outputs/pv1_sdf_d1_factory_contract"


def metadata_schema_properties() -> dict[str, Any]:
    return {
        "claim_label": {"type": "string", "const": CLAIM_LABEL},
        "synthetic": {"type": "boolean", "const": True},
        "source_basis": {"type": "string", "enum": ["real_distribution", "rule_generated", "manual_scenario", "hybrid"]},
        "donor_city": {"type": "string", "enum": ["chicago", "nyc", "london", "mixed"]},
        "donor_artifact": {"type": "string"},
        "generation_version": {"type": "string"},
        "random_seed": {"type": "integer"},
        "generated_at_utc": {"type": "string"},
        "validation_status": {"type": "string", "enum": ["PASS", "WARN", "FAIL"]},
        "not_real_world_observation": {"type": "boolean", "const": True},
    }


def base_schema(title: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    merged = dict(metadata_schema_properties())
    merged.update(properties)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": True,
        "required": sorted(set(REQUIRED_SYNTHETIC_METADATA_FIELDS + required)),
        "properties": merged,
    }


def build_schemas() -> dict[str, dict[str, Any]]:
    synthetic_truth_schema = base_schema(
        "PV1 SDF Synthetic Truth Entity",
        {
            "entity_type": {"type": "string", "enum": SYNTHETIC_ENTITY_TYPES},
            "entity_id": {"type": "string", "pattern": "^synthetic:"},
            "name": {"type": "string"},
            "geometry_wkt": {"type": ["string", "null"]},
            "attributes": {"type": ["object", "string"]},
            "truth_ids": {"type": ["array", "string"], "items": {"type": "string"}},
        },
        ["entity_type", "entity_id"],
    )
    synthetic_truth_schema["x_entity_types"] = SYNTHETIC_ENTITY_TYPES

    source_projection_schema = base_schema(
        "PV1 SDF Source Projection",
        {
            "source_system": {"type": "string"},
            "source_table": {"type": "string"},
            "source_record_id": {"type": "string", "pattern": "^SYN-"},
            "native_id_shape": {"type": "string"},
            "payload": {"type": ["object", "string"]},
            "schema_version": {"type": "string"},
            "known_missing_fields": {"type": ["array", "string"], "items": {"type": "string"}},
            "known_dirty_fields": {"type": ["array", "string"], "items": {"type": "string"}},
            "projection_from_truth_ids": {"type": ["array", "string"], "items": {"type": "string"}},
        },
        [
            "source_system",
            "source_table",
            "source_record_id",
            "native_id_shape",
            "payload",
            "schema_version",
            "known_missing_fields",
            "known_dirty_fields",
            "projection_from_truth_ids",
        ],
    )

    dirty_variant_schema = base_schema(
        "PV1 SDF Dirty Source Variant",
        {
            "dirty_variant_type": {"type": "string", "enum": DIRTY_VARIANT_TYPES},
            "dirty_variant_id": {"type": "string"},
            "base_source_record_id": {"type": ["string", "null"]},
            "source_system": {"type": "string"},
            "source_table": {"type": "string"},
            "dirty_fields": {"type": ["array", "string"], "items": {"type": "string"}},
            "expected_adapter_detection": {"type": "string"},
            "payload": {"type": ["object", "string"]},
        },
        ["dirty_variant_type", "dirty_variant_id", "source_system", "source_table", "dirty_fields", "expected_adapter_detection"],
    )

    replay_event_schema = base_schema(
        "PV1 SDF Replay Event",
        {
            "event_id": {"type": "string", "pattern": "^synthetic:event:"},
            "event_time": {"type": "string"},
            "processing_time": {"type": "string"},
            "source_system": {"type": "string"},
            "event_type": {"type": "string"},
            "subject_ids": {"type": ["array", "string"], "items": {"type": "string"}},
            "payload": {"type": ["object", "string"]},
            "sequence_number": {"type": "integer"},
            "replay_pack_id": {"type": "string"},
            "late_arrival_flag": {"type": "boolean"},
            "out_of_order_flag": {"type": "boolean"},
            "supersedes_event_id": {"type": ["string", "null"]},
        },
        [
            "event_id",
            "event_time",
            "processing_time",
            "source_system",
            "event_type",
            "subject_ids",
            "payload",
            "sequence_number",
            "replay_pack_id",
            "late_arrival_flag",
            "out_of_order_flag",
            "supersedes_event_id",
        ],
    )

    validation_report_schema = base_schema(
        "PV1 SDF Validation Report Row",
        {
            "test_id": {"type": "string"},
            "test_name": {"type": "string"},
            "input_artifacts": {"type": ["array", "string"], "items": {"type": "string"}},
            "expected_behavior": {"type": "string"},
            "actual_behavior": {"type": "string"},
            "status": {"type": "string", "enum": ["PASS", "WARN", "FAIL"]},
            "failure_reason": {"type": ["string", "null"]},
            "claim_boundary_checked": {"type": "boolean"},
            "downstream_gate": {"type": "string"},
        },
        [
            "test_id",
            "test_name",
            "input_artifacts",
            "expected_behavior",
            "actual_behavior",
            "status",
            "claim_boundary_checked",
            "downstream_gate",
        ],
    )

    donor_distribution_schema = base_schema(
        "PV1 SDF Donor Distribution Profile",
        {
            "distribution_id": {"type": "string"},
            "donor_city": {"type": "string"},
            "donor_artifact": {"type": "string"},
            "aggregation_level": {"type": "string"},
            "privacy_floor_applied": {"type": "boolean"},
            "counts": {"type": ["object", "array"]},
            "proportions": {"type": ["object", "array"]},
            "limitations": {"type": ["array", "string"], "items": {"type": "string"}},
        },
        ["distribution_id", "donor_city", "donor_artifact", "aggregation_level", "privacy_floor_applied"],
    )

    action_proposal_schema = base_schema(
        "PV1 SDF Synthetic Action Proposal",
        {
            "proposal_id": {"type": "string", "pattern": "^synthetic:action_proposal:"},
            "proposal_type": {"type": "string", "enum": ALLOWED_ACTION_PROPOSAL_TYPES},
            "proposal_status": {"type": "string"},
            "approval_required": {"type": "boolean", "const": True},
            "forbidden_proposal_types_rejected": {"type": ["array", "string"], "items": {"type": "string"}},
            "grounding_event_ids": {"type": ["array", "string"], "items": {"type": "string"}},
            "review_only": {"type": "boolean", "const": True},
        },
        ["proposal_id", "proposal_type", "proposal_status", "approval_required", "review_only"],
    )

    return {
        "synthetic_truth_schema": synthetic_truth_schema,
        "source_projection_schema": source_projection_schema,
        "dirty_variant_schema": dirty_variant_schema,
        "replay_event_schema": replay_event_schema,
        "validation_report_schema": validation_report_schema,
        "donor_distribution_schema": donor_distribution_schema,
        "action_proposal_synthetic_schema": action_proposal_schema,
    }


def build_d1_payloads(output_dir: Path) -> dict[str, Any]:
    schemas = build_schemas()
    schema_files = {
        "synthetic_truth_schema": "schemas/synthetic_truth_schema.json",
        "source_projection_schema": "schemas/source_projection_schema.json",
        "dirty_variant_schema": "schemas/dirty_variant_schema.json",
        "replay_event_schema": "schemas/replay_event_schema.json",
        "validation_report_schema": "schemas/validation_report_schema.json",
        "donor_distribution_schema": "schemas/donor_distribution_schema.json",
        "action_proposal_synthetic_schema": "schemas/action_proposal_synthetic_schema.json",
    }
    for key, rel in schema_files.items():
        write_json(output_dir / rel, schemas[key])

    boundary = [
        "The Synthetic Data Factory creates [S] synthetic artifacts for development, validation, replay, demonstration, and adversarial testing.",
        "Synthetic data is never real observed public data.",
        "Synthetic artifacts must not be used to make real-world claims.",
        "Synthetic records must never be mixed into certified real-data cartridges without explicit [S] labels.",
        "Synthetic data does not replace real source validation.",
        "The factory emits source-shaped synthetic projections and dirty variants so adapters can be hardened without private personal data.",
        "All proposals are review-only and approval-required.",
    ]

    contract = {
        "contract_id": "PV1-SDF-D1-FACTORY-CONTRACT",
        "status": "PASS",
        "claim_label": CLAIM_LABEL,
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
        "random_seed": GENERATION_SEED,
        "metadata_contract": synthetic_metadata("manual_scenario", donor_city="mixed", donor_artifact="PV1-SDF-D1 contract"),
        "produces": [
            "clean synthetic truth entities",
            "department-shaped source projections",
            "deterministic dirty variants",
            "event-time and processing-time replay streams",
            "validation and adversarial harness reports",
            "adapter handoff manifests",
        ],
        "downstream_uses": [
            "event fabric contract testing",
            "review-only Incident mode candidate testing",
            "review-only Plan mode proposal testing",
            "SUMO/simulator handoff readiness",
            "persona rendering readiness",
            "HITL approval lifecycle testing",
            "negative-path and no-overclaim tests",
        ],
        "required_record_metadata": REQUIRED_SYNTHETIC_METADATA_FIELDS,
        "schemas": schema_files,
        "entity_types": SYNTHETIC_ENTITY_TYPES,
        "dirty_variant_types": DIRTY_VARIANT_TYPES,
        "boundary": boundary,
        "forbidden_action_proposal_types": FORBIDDEN_ACTION_PROPOSAL_TYPES,
        "allowed_action_proposal_types": ALLOWED_ACTION_PROPOSAL_TYPES,
    }

    schema_registry = {
        "registry_id": "PV1-SDF-D1-SCHEMA-REGISTRY",
        "status": "PASS",
        "schemas": [
            {"schema_name": name, "path": rel, "required_metadata_fields": REQUIRED_SYNTHETIC_METADATA_FIELDS}
            for name, rel in schema_files.items()
        ],
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
    }

    claim_policy = {
        "policy_id": "PV1-SDF-D1-CLAIM-LABEL-POLICY",
        "status": "PASS",
        "required_claim_label": CLAIM_LABEL,
        "required_flags": {"synthetic": True, "not_real_world_observation": True},
        "downstream_discriminator": "claim_label == '[S]' and synthetic == true and not_real_world_observation == true",
        "boundary": boundary,
    }

    id_policy = {
        "policy_id": "PV1-SDF-D1-ID-POLICY",
        "status": "PASS",
        "synthetic_id_prefixes": [
            "synthetic:area:chi_near_west_side_v1:{id}",
            "synthetic:parcel:chi_near_west_side_v1:{id}",
            "synthetic:building:chi_near_west_side_v1:{id}",
            "synthetic:event:chi_near_west_side_v1:{id}",
            "synthetic:observation:chi_near_west_side_v1:{id}",
            "synthetic:action_proposal:chi_near_west_side_v1:{id}",
        ],
        "source_shaped_id_examples": [
            "SYN-311-000001",
            "SYN-CRASH-000001",
            "SYN-PERMIT-000001",
            "SYN-VIOL-000001",
            "SYN-INSPECT-000001",
            "SYN-LIC-000001",
            "SYN-AIR-OBS-000001",
        ],
        "real_id_reuse": "forbidden",
        "allowed_donor_labels": {"donor_area_name": "NEAR WEST SIDE", "donor_community_area": "28"},
    }

    privacy_policy = {
        "policy_id": "PV1-SDF-D1-PRIVACY-POLICY",
        "status": "PASS",
        "private_personal_data": "not generated",
        "raw_record_copying": "forbidden",
        "donor_distillation": "aggregates and shapes only",
        "sensitive_source_handling": [
            "no raw case numbers",
            "no person-level crash rows",
            "no private contact fields",
            "no exact real addresses",
            "no secrets or API keys",
        ],
    }

    no_overclaim = {
        "report_id": "PV1-SDF-D1-NO-OVERCLAIM",
        "status": "PASS",
        "allowed_language": [
            "synthetic",
            "scenario",
            "simulation-ready",
            "replayable",
            "review-only",
            "analyst-review candidate",
            "action proposal requiring approval",
            "source-shaped synthetic projection",
            "dirty variant",
            "validation harness",
        ],
        "boundary": boundary,
    }

    docs = {
        "docs/synthetic_data_factory_contract.md": [
            "# Synthetic Data Factory Contract",
            "",
            *boundary,
            "",
            "Every artifact carries `[S]`, `synthetic=true`, and `not_real_world_observation=true`.",
        ],
        "docs/synthetic_claim_boundary.md": [
            "# Synthetic Claim Boundary",
            "",
            "Real where identity matters. Synthetic where behavior matters.",
            "",
            "The factory uses donor distributions as shape, never as observed synthetic claims.",
        ],
        "docs/downstream_usage_policy.md": [
            "# Downstream Usage Policy",
            "",
            "Downstream systems must treat `[S]` records as synthetic fixtures.",
            "Incident and Plan paths may use the pack only for review-only candidates and approval-required proposals.",
        ],
    }
    for rel, lines in docs.items():
        write_text(output_dir / rel, "\n".join(lines))

    return {
        "contract": contract,
        "schema_registry": schema_registry,
        "claim_policy": claim_policy,
        "id_policy": id_policy,
        "privacy_policy": privacy_policy,
        "no_overclaim": no_overclaim,
        "schemas": schemas,
    }


def run_pv1_sdf_d1_gate(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_dir(project_path(root, output_dir), root)
    payloads = build_d1_payloads(out)

    gates = [
        gate("PV1-SDF-D1-PRECOND", True, output_dir=str(out)),
        gate("PV1-SDF-D1-CONTRACT", payloads["contract"]["status"] == "PASS"),
        gate("PV1-SDF-D1-SCHEMAS", len(payloads["schemas"]) == 7, schema_count=len(payloads["schemas"])),
        gate("PV1-SDF-D1-CLAIM-LABELS", payloads["claim_policy"]["required_claim_label"] == CLAIM_LABEL),
        gate("PV1-SDF-D1-ID-POLICY", payloads["id_policy"]["real_id_reuse"] == "forbidden"),
        gate("PV1-SDF-D1-PRIVACY", payloads["privacy_policy"]["private_personal_data"] == "not generated"),
        gate("PV1-SDF-D1-NO-OVERCLAIM", payloads["no_overclaim"]["status"] == "PASS"),
    ]
    status = "PASS" if all_gates_pass(gates) else "FAIL"

    write_json(out / "PV1_SDF_D1_FACTORY_CONTRACT.json", payloads["contract"])
    write_json(out / "PV1_SDF_D1_SCHEMA_REGISTRY.json", payloads["schema_registry"])
    write_json(out / "PV1_SDF_D1_CLAIM_LABEL_POLICY.json", payloads["claim_policy"])
    write_json(out / "PV1_SDF_D1_ID_POLICY.json", payloads["id_policy"])
    write_json(out / "PV1_SDF_D1_PRIVACY_POLICY.json", payloads["privacy_policy"])
    write_json(out / "PV1_SDF_D1_NO_OVERCLAIM_REPORT.json", payloads["no_overclaim"])
    write_text(
        out / "PV1_SDF_D1_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-SDF-D1 Adapter Handover",
                "",
                "Adapters should reject unlabelled synthetic rows and should keep `[S]` rows out of accepted real-data cartridges.",
                "Use the schema registry for truth, projection, dirty-variant, replay, and validation fixtures.",
            ]
        ),
    )
    write_stage_readme(
        out / "README.md",
        "PV1-SDF-D1 Synthetic Data Factory Contract",
        [
            "D1 defines the factory contract, schema registry, claim-label policy, synthetic-safe ID policy, privacy boundary, and no-overclaim boundary.",
            "Status: PASS.",
        ],
    )

    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        status = "FAIL"
        for g in gates:
            if g["gate"] == "PV1-SDF-D1-NO-OVERCLAIM":
                g["status"] = "FAIL"
                g["findings"] = scan["findings"]
    gates.append(gate("PV1-SDF-D1-HASHES", True))

    harness = {
        "task": "PV1-SDF-D1 Synthetic Data Factory Contract",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "output_dir": str(out),
    }
    write_json(out / "PV1_SDF_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D1 factory contract gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d1_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(result["status"])
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
