"""Tests for SupervisorAgent routing policy."""

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_to_researcher_when_no_sources() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "researcher"


def test_supervisor_routes_to_analyst_when_sources_present_no_analysis() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.sources = [SourceDocument(title="Doc 1", snippet="Snippet 1")]
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "analyst"


def test_supervisor_routes_to_writer_when_analysis_present() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.sources = [SourceDocument(title="Doc 1", snippet="Snippet 1")]
    state.analysis_notes = "Analysis note"
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "writer"


def test_supervisor_routes_to_done_when_final_answer_present() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.final_answer = "This is the final answer."
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "done"
