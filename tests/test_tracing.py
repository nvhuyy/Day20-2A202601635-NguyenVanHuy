"""Tests for trace_span and tracing integration."""

import pytest

from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.core.tracing import trace_span as core_trace_span
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.observability.tracing import trace_span


def test_trace_span_basic() -> None:
    attributes = {"model": "gpt-4o-mini", "user_id": "test_user"}
    with trace_span("test_operation", attributes) as span:
        assert span["name"] == "test_operation"
        assert span["attributes"]["model"] == "gpt-4o-mini"
        assert span["attributes"]["user_id"] == "test_user"
        span["custom_output"] = 42

    assert span["duration_seconds"] is not None
    assert span["duration_seconds"] >= 0
    assert span["custom_output"] == 42


def test_trace_span_nested() -> None:
    with trace_span("parent_span", {"layer": "parent"}) as parent:
        with trace_span("child_span", {"layer": "child"}) as child:
            child["status"] = "ok"
        parent["child_status"] = child["status"]

    assert parent["duration_seconds"] is not None
    assert child["duration_seconds"] is not None
    assert parent["child_status"] == "ok"


def test_trace_span_captures_exception() -> None:
    span_ref = None
    with (
        pytest.raises(ValueError, match="Something went wrong"),
        trace_span("failing_operation", {"attempt": 1}) as span,
    ):
        span_ref = span
        raise ValueError("Something went wrong")

    assert span_ref is not None
    assert span_ref["error"] == "Something went wrong"
    assert span_ref["duration_seconds"] is not None


def test_core_tracing_alias() -> None:
    with core_trace_span("core_alias_test") as span:
        assert span["name"] == "core_alias_test"
    assert span["duration_seconds"] is not None


def test_benchmark_tracing() -> None:
    def dummy_runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        state.final_answer = f"Answer to {query}"
        return state

    state, metrics = run_benchmark("unit_test_run", "What is AI?", dummy_runner)
    assert metrics.run_name == "unit_test_run"
    assert metrics.latency_seconds > 0
    assert state.final_answer == "Answer to What is AI?"
