from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self) -> None:
        self.search_client = SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        query = state.request.query
        max_sources = state.request.max_sources

        try:
            # -----------------------------------------------------
            # 1. Search
            # -----------------------------------------------------

            sources = self.search_client.search(
                query=query,
                max_results=max_sources,
            )

            # -----------------------------------------------------
            # 2. Basic source filtering
            # -----------------------------------------------------

            filtered_sources = self._filter_sources(
                sources,
                max_sources=max_sources,
            )

            state.sources = filtered_sources

            # -----------------------------------------------------
            # 3. Create concise research notes
            # -----------------------------------------------------

            state.research_notes = self._build_research_notes(
                query=query,
                sources=filtered_sources,
            )

            # -----------------------------------------------------
            # 4. Trace
            # -----------------------------------------------------

            state.add_trace_event(
                "researcher.search",
                {
                    "query": query,
                    "requested_sources": max_sources,
                    "sources_found": len(sources),
                    "sources_kept": len(filtered_sources),
                },
            )

            return state

        except Exception as exc:
            state.errors.append(
                f"Researcher failed: {exc}"
            )

            state.add_trace_event(
                "researcher.error",
                {
                    "query": query,
                    "error": str(exc),
                },
            )

            return state

    @staticmethod
    def _filter_sources(
        sources: list[SourceDocument],
        max_sources: int,
    ) -> list[SourceDocument]:
        """Remove malformed and duplicate sources."""

        filtered: list[SourceDocument] = []
        seen_urls: set[str] = set()

        for source in sources:
            # Require useful source information.
            if not source.title.strip():
                continue

            if not source.snippet.strip():
                continue

            # Deduplicate by URL.
            if source.url:
                if source.url in seen_urls:
                    continue

                seen_urls.add(source.url)

            filtered.append(source)

            if len(filtered) >= max_sources:
                break

        return filtered

    @staticmethod
    def _build_research_notes(
        query: str,
        sources: list[SourceDocument],
    ) -> str:
        """Create compact notes from retrieved sources.

        This does not ask an LLM to summarize the sources. It simply
        preserves the retrieved evidence so that a later analyst/writer
        agent can reason over it.
        """

        if not sources:
            return (
                f"No reliable sources were found for the query: {query}"
            )

        lines = [
            f"Research query: {query}",
            "",
            "Retrieved sources:",
        ]

        for index, source in enumerate(sources, start=1):
            lines.append(
                f"{index}. {source.title}"
            )

            if source.url:
                lines.append(
                    f"   URL: {source.url}"
                )

            lines.append(
                f"   Evidence: {source.snippet}"
            )

        return "\n".join(lines)
    