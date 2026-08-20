"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import os
from dataclasses import dataclass

from openai import OpenAI

from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.observability.tracing import trace_span


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client.

    The rest of the application only interacts with this class and does not
    need to know which LLM provider is being used.

    Environment variables:
        OPENAI_API_KEY: API key
        OPENAI_MODEL: Model name
        OPENAI_BASE_URL: Optional OpenAI-compatible API endpoint
        LLM_TIMEOUT: Request timeout in seconds
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise StudentTodoError(
                "Missing OPENAI_API_KEY environment variable"
            )

        self.api_key: str = resolved_api_key
        self.model: str = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")

        self.client = OpenAI(
            api_key=self.api_key,
            timeout=timeout,
            base_url=self.base_url,
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """Return a model completion with tracing.

        Retry, timeout, and token logging should be handled here rather
        than inside agents.
        """

        with trace_span(
            "llm.complete",
            {
                "model": self.model,
                "system_prompt_length": len(system_prompt),
                "user_prompt_length": len(user_prompt),
            },
        ) as span:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                )
            except Exception as exc:
                span["error"] = str(exc)
                raise StudentTodoError(
                    f"LLM request failed: {exc}"
                ) from exc

            choice = response.choices[0]
            usage = response.usage

            input_tokens = (
                usage.prompt_tokens
                if usage is not None
                else None
            )

            output_tokens = (
                usage.completion_tokens
                if usage is not None
                else None
            )

            span["input_tokens"] = input_tokens
            span["output_tokens"] = output_tokens
            span["total_tokens"] = (input_tokens or 0) + (output_tokens or 0)

            return LLMResponse(
                content=choice.message.content or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=None,
            )
    