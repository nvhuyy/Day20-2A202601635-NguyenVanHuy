"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    name = "supervisor"

    def __init__(self) -> None:
        self.settings = get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        if state.final_answer or state.iteration >= self.settings.max_iterations:
            next_route = "done"

        elif state.errors:
            if state.sources or state.analysis_notes or state.research_notes:
                next_route = "writer"
            else:
                next_route = "done"

        elif not state.sources:
            next_route = "researcher"

        elif not state.analysis_notes:
            next_route = "analyst"

        else:
            next_route = "writer"

        state.record_route(next_route)

        return state
