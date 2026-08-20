"""LangGraph workflow."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

        self.supervisor = SupervisorAgent()
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()

    def build(self) -> Any:
        """Create and compile the LangGraph graph."""

        graph = StateGraph(ResearchState)

        # ---------------------------------------------------------
        # Nodes
        # ---------------------------------------------------------

        graph.add_node(
            "supervisor",
            self._run_supervisor,
        )

        graph.add_node(
            "researcher",
            self._run_researcher,
        )

        graph.add_node(
            "analyst",
            self._run_analyst,
        )

        graph.add_node(
            "writer",
            self._run_writer,
        )

        # ---------------------------------------------------------
        # Entry point
        # ---------------------------------------------------------

        graph.add_edge(
            START,
            "supervisor",
        )

        # ---------------------------------------------------------
        # Supervisor decides what runs next.
        # ---------------------------------------------------------

        graph.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        # ---------------------------------------------------------
        # Every worker returns to supervisor.
        # ---------------------------------------------------------

        graph.add_edge(
            "researcher",
            "supervisor",
        )

        graph.add_edge(
            "analyst",
            "supervisor",
        )

        graph.add_edge(
            "writer",
            "supervisor",
        )

        return graph.compile()

    # =============================================================
    # Node wrappers
    # =============================================================

    def _run_supervisor(
        self,
        state: ResearchState,
    ) -> ResearchState:
        """Run supervisor with tracing."""

        with trace_span(
            "supervisor",
            {
                "iteration": state.iteration,
                "has_sources": bool(state.sources),
                "has_analysis": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
                "error_count": len(state.errors),
            },
        ) as span:

            result = self.supervisor.run(state)

            if result.route_history:
                span["next_route"] = result.route_history[-1]

            span["iteration"] = result.iteration

            return result

    def _run_researcher(
        self,
        state: ResearchState,
    ) -> ResearchState:
        """Run researcher with tracing."""

        with trace_span(
            "researcher",
            {
                "query": state.request.query,
                "max_sources": state.request.max_sources,
            },
        ) as span:

            result = self.researcher.run(state)

            span["source_count"] = len(result.sources)
            span["has_research_notes"] = bool(
                result.research_notes
            )

            return result

    def _run_analyst(
        self,
        state: ResearchState,
    ) -> ResearchState:
        """Run analyst with tracing."""

        with trace_span(
            "analyst",
            {
                "source_count": len(state.sources),
                "has_research_notes": bool(
                    state.research_notes
                ),
            },
        ) as span:

            result = self.analyst.run(state)

            span["has_analysis_notes"] = bool(
                result.analysis_notes
            )

            return result

    def _run_writer(
        self,
        state: ResearchState,
    ) -> ResearchState:
        """Run writer with tracing."""

        with trace_span(
            "writer",
            {
                "source_count": len(state.sources),
                "has_analysis_notes": bool(
                    state.analysis_notes
                ),
            },
        ) as span:

            result = self.writer.run(state)

            span["has_final_answer"] = bool(
                result.final_answer
            )

            return result

    # =============================================================
    # Conditional routing
    # =============================================================

    def _route_from_supervisor(
        self,
        state: ResearchState,
    ) -> str:
        """Return the route selected by the supervisor."""

        if not state.route_history:
            return "done"

        route = state.route_history[-1]

        if state.iteration >= self.settings.max_iterations:
            return "done"

        if route in {
            "researcher",
            "analyst",
            "writer",
            "done",
        }:
            return route

        state.errors.append(
            f"Supervisor returned unknown route: {route}"
        )

        return "done"

    # =============================================================
    # Execution
    # =============================================================

    def run(
        self,
        state: ResearchState,
    ) -> ResearchState:
        """Execute the graph and return final state."""

        with trace_span(
            "multi-agent-research",
            {
                "query": state.request.query,
                "max_sources": state.request.max_sources,
            },
        ) as span:

            graph = self.build()

            try:
                result: Any = graph.invoke(state)

            except Exception as exc:
                state.errors.append(
                    f"Workflow execution failed: {exc}"
                )

                span["error"] = str(exc)

                return state

            if isinstance(result, ResearchState):
                final_state = result
            else:
                final_state = ResearchState.model_validate(result)

            # Add final workflow-level information.
            span["iterations"] = final_state.iteration
            span["route_history"] = final_state.route_history
            span["source_count"] = len(final_state.sources)
            span["has_final_answer"] = bool(
                final_state.final_answer
            )
            span["error_count"] = len(final_state.errors)

            return final_state
        