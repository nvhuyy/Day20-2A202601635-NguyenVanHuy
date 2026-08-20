"""Command-line entrypoint for the lab starter."""

import time
from typing import Annotated

import typer
from dotenv import load_dotenv
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()

load_dotenv()

def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a minimal single-agent baseline placeholder."""

    _init()

    # 1. Parse CLI input into the shared request schema.
    request = _parse_query(query)

    # 2. Initialize workflow state.
    state = ResearchState(request=request)

    # 3. Create the provider-agnostic LLM client.
    llm = LLMClient()

    system_prompt = f"""
You are a research assistant helping {request.audience}.

Answer the user's research question clearly, accurately, and concisely.

Requirements:
- Directly answer the research question.
- Explain important concepts when necessary.
- Do not invent facts, sources, citations, URLs, numbers, or references.
- If you are uncertain about something, explicitly state the uncertainty.
- Structure the answer so that it is easy to understand.

This is a single-agent baseline. Do not use external tools or delegate
the task to other agents.
""".strip()

    user_prompt = request.query

    # 4. Record that the baseline agent started.
    state.record_route("baseline")

    start = time.perf_counter()

    with trace_span(
        "baseline",
        {
            "query": request.query,
            "model": llm.model,
            "audience": request.audience,
        },
    ) as span:
        try:
            # 5. The actual end-to-end LLM call.
            response = llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            latency_seconds = time.perf_counter() - start

            # 6. Store the final answer in the shared state.
            state.final_answer = response.content

            # 7. Record the LLM result as an AgentResult.
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                        "latency_seconds": latency_seconds,
                    },
                )
            )

            # 8. Record execution information in the state trace.
            state.add_trace_event(
                "baseline.llm_complete",
                {
                    "latency_seconds": latency_seconds,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )

            span["latency_seconds"] = latency_seconds
            span["input_tokens"] = response.input_tokens
            span["output_tokens"] = response.output_tokens
            span["has_final_answer"] = bool(state.final_answer)

        except Exception as exc:
            latency_seconds = time.perf_counter() - start

            state.errors.append(str(exc))
            span["error"] = str(exc)

            state.add_trace_event(
                "baseline.llm_error",
                {
                    "latency_seconds": latency_seconds,
                    "error": str(exc),
                },
            )

            raise typer.Exit(code=1) from exc

    # 9. Display the final answer.
    console.print(
        Panel.fit(
            state.final_answer,
            title="Single-Agent Baseline",
        )
    )

    # 10. Display basic benchmark information.
    console.print(
        f"Latency: {latency_seconds:.3f}s"
    )
    console.print(
        f"Input tokens: {response.input_tokens}"
    )
    console.print(
        f"Output tokens: {response.output_tokens}"
    )
    console.print(
        f"Cost: {response.cost_usd}"
    )


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=_parse_query(query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
