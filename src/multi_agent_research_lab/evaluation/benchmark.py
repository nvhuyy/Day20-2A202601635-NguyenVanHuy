"""Benchmark skeleton for single-agent vs multi-agent."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return a placeholder metric object with tracing.

    (student): Add quality scoring, estimated token cost, citation coverage, and error rate.
    """

    with trace_span(
        "benchmark.run",
        {
            "run_name": run_name,
            "query": query,
        },
    ) as span:
        started = perf_counter()
        state = runner(query)
        latency = perf_counter() - started
        metrics = BenchmarkMetrics(
            run_name=run_name,
            latency_seconds=latency,
            failure_rate=1.0 if state.errors else 0.0,
        )

        span["latency_seconds"] = latency
        span["has_final_answer"] = bool(state.final_answer)
        span["error_count"] = len(state.errors)

        return state, metrics
