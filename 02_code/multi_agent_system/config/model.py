"""Configure LLM instances for discussion and vote-checking agents."""

import asyncio
import os
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient

from .metrics import logger, metrics

MODEL_MAX_ATTEMPTS = max(1, int(os.getenv("MODEL_MAX_ATTEMPTS", "4")))
MODEL_RETRY_BASE_DELAY = float(os.getenv("MODEL_RETRY_BASE_DELAY", "5"))


def _is_retryable_llm_error(error: Exception) -> bool:
    """Return True for transient provider/network errors worth retrying."""
    error_name = error.__class__.__name__.lower()
    error_text = str(error).lower()
    retryable_markers = (
        "timeout",
        "connection",
        "rate limit",
        "ratelimit",
        "429",
        "500",
        "502",
        "503",
        "504",
        "badgateway",
        "serviceunavailable",
        "internalserver",
    )
    return any(marker in error_name or marker in error_text for marker in retryable_markers)


class TokenTrackingLiteLLMClient(LiteLLMClient):
    """Minimal token logging from LiteLLM responses."""

    async def acompletion(self, model, messages, tools=None, **kwargs):
        """Run an async completion and record response token usage if present."""
        for attempt in range(1, MODEL_MAX_ATTEMPTS + 1):
            try:
                response = await super().acompletion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    **kwargs,
                )
                break
            except Exception as error:
                if attempt >= MODEL_MAX_ATTEMPTS or not _is_retryable_llm_error(error):
                    raise

                delay = MODEL_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Transient LLM error on attempt %s/%s; retrying in %.1fs: %s",
                    attempt,
                    MODEL_MAX_ATTEMPTS,
                    delay,
                    error,
                )
                await asyncio.sleep(delay)

        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            metrics.add_tokens(prompt_tokens, completion_tokens)

        return response


DISCUSSION_MODEL = LiteLlm(
    model=os.getenv("OPEN_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    api_base=os.getenv("NIM_BASE_URL"),
    llm_client=TokenTrackingLiteLLMClient(),
    stream_options={"include_usage": True},
    temperature=float(os.getenv("MODEL_TEMPERATURE"))
)
