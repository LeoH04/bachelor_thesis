"""Configure LLM instances for discussion and vote-checking agents."""

import os
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient

from .metrics import metrics
from .run_warnings import record_run_warning

_LITELLM_ROLES = {
    "assistant",
    "developer",
    "function",
    "system",
    "tool",
    "user",
}


def _sanitize_message_roles(messages: object) -> object:
    """Strip GPT-OSS/Harmony channel suffixes from message roles."""
    if not isinstance(messages, list):
        return messages

    sanitized_messages = []
    changed = False
    for message in messages:
        if isinstance(message, dict):
            role = message.get("role")
            if isinstance(role, str) and "<|" in role:
                base_role = role.split("<|", 1)[0]
                if base_role in _LITELLM_ROLES:
                    message = dict(message)
                    message["role"] = base_role
                    changed = True

        sanitized_messages.append(message)

    return sanitized_messages if changed else messages


def _response_usage(response: object) -> object | None:
    """Extract token usage from common response shapes."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    return usage


def _usage_value(usage: object, *keys: str) -> int | None:
    """Return one integer usage value from object or dict usage metadata."""
    for key in keys:
        value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def _token_counts_from_usage(usage: object) -> tuple[int, int, list[str]]:
    """Return input/output token counts and missing field labels."""
    input_tokens = _usage_value(usage, "prompt_tokens", "input_tokens")
    output_tokens = _usage_value(usage, "completion_tokens", "output_tokens")
    total_tokens = _usage_value(usage, "total_tokens")

    if input_tokens is None and total_tokens is not None and output_tokens is not None:
        input_tokens = max(total_tokens - output_tokens, 0)
    if output_tokens is None and total_tokens is not None and input_tokens is not None:
        output_tokens = max(total_tokens - input_tokens, 0)

    missing_fields = []
    if input_tokens is None:
        missing_fields.append("prompt_tokens")
        input_tokens = 0
    if output_tokens is None:
        missing_fields.append("completion_tokens")
        output_tokens = 0

    return input_tokens, output_tokens, missing_fields


class TokenTrackingLiteLLMClient(LiteLLMClient):
    """Minimal token logging from LiteLLM responses."""

    async def acompletion(self, model, messages, tools=None, **kwargs):
        """Run an async completion and record response token usage if present."""
        messages = _sanitize_message_roles(messages)

        response = await super().acompletion(
            model=model,
            messages=messages,
            tools=tools,
            **kwargs,
        )

        usage = _response_usage(response)
        if not usage:
            record_run_warning(
                "token_usage_missing",
                "Model response did not include token usage; token totals were not updated for this call.",
                model=str(model),
            )
            return response

        prompt_tokens, completion_tokens, missing_fields = _token_counts_from_usage(usage)
        if missing_fields:
            record_run_warning(
                "token_usage_fields_missing",
                "Model response token usage was missing required fields; missing fields were counted as zero.",
                model=str(model),
                missing_fields=missing_fields,
                usage=usage,
            )

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
