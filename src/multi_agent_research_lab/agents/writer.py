"""Writer agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self) -> None:
        self.llm = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesize the research and analysis into a clear answer.
        Citations must refer only to sources present in state.sources.
        """

        if not state.research_notes:
            state.errors.append(
                "Writer cannot run because research_notes is empty."
            )

            state.add_trace_event(
                "writer.error",
                {
                    "error": "Missing research_notes",
                },
            )

            return state

        if not state.analysis_notes:
            state.errors.append(
                "Writer cannot run because analysis_notes is empty."
            )

            state.add_trace_event(
                "writer.error",
                {
                    "error": "Missing analysis_notes",
                },
            )

            return state

        source_context = self._build_source_context(state)

        system_prompt = """
You are the final writer in a research workflow.

Your task is to write the final answer to the user's research question
using ONLY the research evidence and analysis provided.

Requirements:

1. Directly answer the user's question.
2. Be clear, concise, and well structured.
3. Preserve important nuance and uncertainty from the analysis.
4. Do not invent facts, citations, URLs, or sources.
5. Every factual claim that depends on retrieved research should have
   an inline citation.
6. Citations MUST refer only to the numbered sources provided below.
7. Use citations in the form [1], [2], [3], etc.
8. Never create a citation number that does not exist in the source list.
9. If sources disagree, explicitly mention the disagreement.
10. Do not present weak or unsupported evidence as established fact.
11. At the end, include a "Sources" section mapping citation numbers
    to the corresponding source titles and URLs.
12. If a source has no URL, cite it by title only.

Do not mention this internal workflow or the agents.
""".strip()

        user_prompt = f"""
User's research question:
{state.request.query}

Research notes:
{state.research_notes}

Analysis notes:
{state.analysis_notes}

Available sources:
{source_context}

Write the final answer now.
""".strip()

        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            state.final_answer = response.content

            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )

            state.add_trace_event(
                "writer.complete",
                {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                    "source_count": len(state.sources),
                },
            )

        except Exception as exc:
            state.errors.append(
                f"Writer failed: {exc}"
            )

            state.add_trace_event(
                "writer.error",
                {
                    "error": str(exc),
                },
            )

        return state

    @staticmethod
    def _build_source_context(state: ResearchState) -> str:
        """Build numbered source context for citation generation."""

        if not state.sources:
            return "No sources are available."

        lines: list[str] = []

        for index, source in enumerate(state.sources, start=1):
            lines.append(
                f"[{index}] {source.title}"
            )

            if source.url:
                lines.append(
                    f"URL: {source.url}"
                )

            lines.append(
                f"Evidence: {source.snippet}"
            )

            score = source.metadata.get("score")

            if score is not None:
                lines.append(
                    f"Tavily relevance score: {score}"
                )

            lines.append("")

        return "\n".join(lines)
    