"""Future-flow skeleton descriptors for ASK v1.1 contract tests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FutureFlowNotImplementedError(RuntimeError):
    """Raised when a skeleton-only future flow is invoked."""


class FutureFlowSkeleton(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: str
    version: str = "1.0"
    gates: list[str] = Field(default_factory=list)
    entry_contract: str = "reserved"
    exit_contract: str = "reserved"
    not_implemented_reason: str
    runtime_executor: None = None
    templates: list[str] = Field(default_factory=list)
    retrieval_plan: None = None
    action_adapter: None = None
    llm_enabled: bool = False
    data_adapters: list[str] = Field(default_factory=list)
    state_mutation: bool = False


FUTURE_FLOW_SKELETONS: tuple[FutureFlowSkeleton, ...] = (
    FutureFlowSkeleton(
        flow_id="flow:watch_v1",
        gates=["not_implemented"],
        not_implemented_reason="Skeleton contract only; no watch runtime, notification, or monitor logic.",
    ),
    FutureFlowSkeleton(
        flow_id="flow:brief_v1",
        gates=["not_implemented"],
        not_implemented_reason="Skeleton contract only; no briefing generation runtime.",
    ),
    FutureFlowSkeleton(
        flow_id="flow:diff_v1",
        gates=["not_implemented"],
        not_implemented_reason="Skeleton contract only; no diff computation runtime.",
    ),
    FutureFlowSkeleton(
        flow_id="flow:incident_v1",
        gates=["not_implemented"],
        not_implemented_reason="Skeleton contract only; no incident response, dispatch, or ticket runtime.",
    ),
)

IMPLEMENTED_FLOWS: tuple[str, ...] = ("flow:ask_v1",)


def list_future_flow_skeletons() -> list[FutureFlowSkeleton]:
    return [flow.model_copy(deep=True) for flow in FUTURE_FLOW_SKELETONS]


def get_future_flow_skeleton(flow_id: str) -> FutureFlowSkeleton:
    for flow in FUTURE_FLOW_SKELETONS:
        if flow.flow_id == flow_id:
            return flow.model_copy(deep=True)
    raise KeyError(f"unknown future-flow skeleton: {flow_id}")


def assert_skeleton_only(flow: FutureFlowSkeleton) -> bool:
    if flow.runtime_executor is not None:
        raise AssertionError(f"{flow.flow_id} has runtime executor")
    if flow.templates:
        raise AssertionError(f"{flow.flow_id} has templates")
    if flow.retrieval_plan is not None:
        raise AssertionError(f"{flow.flow_id} has retrieval plan")
    if flow.action_adapter is not None:
        raise AssertionError(f"{flow.flow_id} has action adapter")
    if flow.llm_enabled:
        raise AssertionError(f"{flow.flow_id} enables LLM runtime")
    if flow.data_adapters:
        raise AssertionError(f"{flow.flow_id} has data adapters")
    if flow.state_mutation:
        raise AssertionError(f"{flow.flow_id} has state mutation")
    if "not_implemented" not in flow.gates:
        raise AssertionError(f"{flow.flow_id} is not marked not_implemented")
    return True


def assert_all_skeletons_only() -> bool:
    return all(assert_skeleton_only(flow) for flow in list_future_flow_skeletons())


def run_future_flow_skeleton(flow_id: str) -> None:
    flow = get_future_flow_skeleton(flow_id)
    assert_skeleton_only(flow)
    raise FutureFlowNotImplementedError(
        f"{flow.flow_id} is skeleton-only and has no runtime executor."
    )


def ask_v1_is_only_implemented_flow() -> bool:
    return IMPLEMENTED_FLOWS == ("flow:ask_v1",)
