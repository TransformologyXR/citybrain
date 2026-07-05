# Epoch 1 Canonical State Reconciliation

Status: PASS_WITH_LIMITATIONS

Frozen shapes indexed: 26

| Shape | Canonical Status | Proof |
| --- | --- | --- |
| ASK v1.1 AnswerPacket/app handoff shapes | canonical | packages/ask_v11; apps/web-control-room/src/askV11 |
| Event Fabric R0.1 imported/owned contracts | canonical | contracts/event_fabric_r0_1; packages/event_fabric_r0_1_validator |
| CandidateObservation | canonical | packages/event_fabric/contracts.py; R7 ingestion scripts |
| EventEnvelope | canonical | contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_EVENT_ENVELOPE_SCHEMA.json |
| MaterializedReviewState | canonical | contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_MATERIALIZED_REVIEW_STATE_SCHEMA.json |
| QueryResultPacket | canonical | contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_QUERY_RESULT_PACKET_SCHEMA.json |
| OverlayPacket | canonical | contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_OVERLAY_PACKET_SCHEMA.json |
| CheckReport / CHECK v0 | canonical | outputs/push2_lane_a_check_authority_v1/CHECK_V0_SCHEMA.json |
| AuthorityEnvelope v1 | canonical | outputs/push2_lane_a_check_authority_v1/AUTHORITY_ENVELOPE_V1_SCHEMA.json |
| WatchItem | canonical | outputs/push2_lane_b_watch_scout_v1 |
| DispositionEvent | canonical | outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json |
| BRIEF v2 | canonical | outputs/push3_lane_a_brief_v2_flow1_packaging |
| SelectedItemWorkspace / SourceRecord360 | canonical | outputs/push3_lane_b_cockpit_source_record_360 |
| DiffItem | canonical | outputs/push3_lane_c_diff_recall_readonly |
| RecallMatchItem | canonical | outputs/push3_lane_c_diff_recall_readonly |
| CER AttributeAssertion / AttributeConflict / MatchCandidate | canonical | packages/cer; outputs/push4_lane_a_cer_engine |
| Semantic Graph v2 Node/Edge/DependencyEdge | canonical | packages/semantic_graph; outputs/push4_lane_b_semantic_graph_v2 |
| CHECK v1 Report | canonical | packages/check_v1; outputs/push4_lane_c_check_v1 |
| MediaEvidenceBundle | canonical | outputs/push5_lane_b_perception_media_evidence |
| WorkflowStateEvent | canonical | outputs/push5_lane_c_watch_workflow_state |
| ApprovalRequest / ApprovalDecision / Authority Level 3 | canonical | packages/approval_lifecycle; outputs/push6_lane_a_approval_lifecycle |
| OptionSetV2 / PlanOption | canonical | packages/plan_mode; outputs/push6_lane_b_plan_mode |
| ScheduleOption / ScenarioPacket / SimulationRunRecord | canonical | outputs/push6_lane_c_schedule_simulate |
| FederatedPacketEnvelope / DataMaturityScore / DepartmentLocalNode | canonical | packages/federation; outputs/push7_lane_a_federation_data_maturity |
| RBAC Role/Permission/AuditEvent | canonical | outputs/push7_lane_b_rbac_audit_observability |
| ExecutionAdapterRegistry / AdapterPreflight / ConditionalAutonomyPreflight | canonical | outputs/push7_lane_c_execution_readiness_autonomy_preflight |
