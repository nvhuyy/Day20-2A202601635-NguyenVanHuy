"""Search client abstraction for ResearcherAgent."""

from tavily import TavilyClient

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import SourceDocument
from multi_agent_research_lab.observability.tracing import trace_span


class SearchClient:
    """Provider-agnostic search client backed by Tavily."""

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.tavily_api_key:
            raise StudentTodoError(
                "TAVILY_API_KEY is not configured."
            )

        self.client = TavilyClient(
            api_key=settings.tavily_api_key
        )

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SourceDocument]:
        """Search Tavily and convert results to SourceDocument with tracing."""

        if not query.strip():
            return []

        with trace_span(
            "search.tavily",
            {
                "query": query,
                "max_results": max_results,
            },
        ) as span:
            try:
                response = self.client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="advanced",
                    include_answer=False,
                    include_raw_content=False,
                )
            except Exception as exc:
                span["error"] = str(exc)
                raise StudentTodoError(
                    f"Tavily search failed: {exc}"
                ) from exc

            documents: list[SourceDocument] = []

            for result in response.get("results", []):
                title = result.get("title", "").strip()
                url = result.get("url")
                snippet = (
                    result.get("content")
                    or result.get("snippet")
                    or ""
                ).strip()

                # Ignore malformed results.
                if not title or not snippet:
                    continue

                documents.append(
                    SourceDocument(
                        title=title,
                        url=url,
                        snippet=snippet,
                        metadata={
                            "score": result.get("score"),
                            "source": "tavily",
                        },
                    )
                )

            span["results_count"] = len(documents)
            return documents
    