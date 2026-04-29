import os
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient

from .metrics import metrics


class TokenTrackingLiteLLMClient(LiteLLMClient):
    """Minimal token logging from LiteLLM responses."""

    async def acompletion(self, model, messages, tools=None, **kwargs):
        response = await super().acompletion(
            model=model,
            messages=messages,
            tools=tools,
            **kwargs,
        )

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
)

VOTE_MODEL = LiteLlm(
    model=os.getenv("OPEN_MODEL"),
    api_key=os.getenv("NVIDIA_API_KEY"),
    api_base=os.getenv("NIM_BASE_URL"),
)