"""Analyst agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self) -> None:
        self.llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Analyze research notes, compare sources, and identify weak
        or conflicting evidence.
        """

        if not state.research_notes:
            state.errors.append(
                "Analyst cannot run because research_notes is empty."
            )

            state.add_trace_event(
                "analyst.error",
                {
                    "error": "Missing research_notes",
                },
            )

            return state

        # Build explicit source information so the LLM can evaluate
        # provenance instead of seeing only a flattened text blob.
        source_context = self._build_source_context(state)

        system_prompt = """
You are an analytical research agent.

Your task is to analyze retrieved research evidence and produce
structured analysis notes for a downstream writer.

You MUST:
1. Identify the key claims supported by the sources.
2. Compare sources when they discuss the same claim.
3. Identify agreements and disagreements between sources.
4. Evaluate source reliability using observable evidence such as:
   - source authority,
   - relevance,
   - specificity,
   - freshness when available,
   - consistency with other sources.
5. Flag weak, unsupported, ambiguous, or conflicting claims.
6. Distinguish facts directly supported by sources from inference.
7. Never invent facts, citations, URLs, or source details.

Do not write the final answer to the user.
Produce analytical notes that another agent can use to write the
final response.
""".strip()

        user_prompt = f"""
Research query:
{state.request.query}

Research notes:
{state.research_notes}

Retrieved sources:
{source_context}

Analyze the evidence and return structured analysis notes.
""".strip()

        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            state.analysis_notes = response.content

            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )

            state.add_trace_event(
                "analyst.complete",
                {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                    "source_count": len(state.sources),
                },
            )

        except Exception as exc:
            state.errors.append(
                f"Analyst failed: {exc}"
            )

            state.add_trace_event(
                "analyst.error",
                {
                    "error": str(exc),
                },
            )

        return state

    @staticmethod
    def _build_source_context(state: ResearchState) -> str:
        """Build a provenance-preserving representation of sources."""

        if not state.sources:
            return "No sources available."

        lines: list[str] = []

        for index, source in enumerate(state.sources, start=1):
            lines.append(
                f"Source {index}:"
            )
            lines.append(
                f"Title: {source.title}"
            )

            if source.url:
                lines.append(
                    f"URL: {source.url}"
                )

            lines.append(
                f"Snippet: {source.snippet}"
            )

            score = source.metadata.get("score")

            if score is not None:
                lines.append(
                    f"Tavily relevance score: {score}"
                )

            lines.append("")

        return "\n".join(lines)
    