"""Tracing hooks.

This module provides a provider-agnostic tracing interface.
Langfuse is used as the current tracing backend with local fallback support.
"""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from time import perf_counter
from typing import Any


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Create a tracing span backed by Langfuse (with safe local fallback).

    The returned dictionary remains compatible with the original
    skeleton and can be used by the application for local tracing.

    Langfuse configuration is loaded from environment variables:
        LANGFUSE_PUBLIC_KEY
        LANGFUSE_SECRET_KEY
        LANGFUSE_BASE_URL (or LANGFUSE_HOST)
    """

    started = perf_counter()

    span: dict[str, Any] = {
        "name": name,
        "attributes": dict(attributes or {}),
        "duration_seconds": None,
    }

    langfuse_client = None
    try:
        from langfuse import get_client

        langfuse_client = get_client()
    except Exception:
        langfuse_client = None

    if langfuse_client is not None:
        try:
            with langfuse_client.start_as_current_observation(
                as_type="span",
                name=name,
                metadata=span["attributes"],
            ) as lf_span:
                span["trace_id"] = getattr(lf_span, "trace_id", None)
                span["span_id"] = getattr(lf_span, "id", None)

                yield span

                # Store local span information in Langfuse.
                output_data = {
                    k: v
                    for k, v in span.items()
                    if k not in {"name", "attributes", "trace_id", "span_id"}
                }
                output_data["duration_seconds"] = perf_counter() - started
                with suppress(Exception):
                    lf_span.update(
                        output=output_data,
                        metadata=span.get("attributes"),
                    )
        except Exception as exc:
            span["error"] = str(exc)
            raise
        finally:
            span["duration_seconds"] = perf_counter() - started
    else:
        try:
            yield span
        except Exception as exc:
            span["error"] = str(exc)
            raise
        finally:
            span["duration_seconds"] = perf_counter() - started