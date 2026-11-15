"""Claude client for our own methods (long context, BM25, GRAFT). Calls go through the gateway,
which forwards them to the Anthropic API (or the fake backend) and logs tokens and cost.

Differences from the benchmark's own Claude path (agent.py `_query_claude`), all deliberate:
- no `temperature`: the API rejects sampling parameters since 2026-10-21;
- the system prompt is sent (the benchmark drops it for Claude via `include_system=False`);
- thinking is disabled, so a short answer cap is not spent on thinking.
The API key is only needed by the gateway, which reads `ANTHROPIC_API_KEY` from the environment.
"""

import time
from dataclasses import dataclass

import anthropic


@dataclass
class LLMCall:
    text: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    latency_s: float


class ClaudeLLM:
    def __init__(self, gateway_url: str, model: str, max_retries: int = 5):
        self.model = model
        # the gateway holds the real key; the SDK only needs a placeholder to talk to it
        self.client = anthropic.Anthropic(base_url=gateway_url, api_key="via-gateway", max_retries=max_retries)

    def complete(self, system: str, user: str | list[dict], max_tokens: int) -> LLMCall:
        """`user` is plain text, or content blocks (e.g. to mark a long prefix for prompt caching)."""
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": user}],
        )
        return LLMCall(
            text="".join(block.text for block in response.content if block.type == "text"),
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_s=time.time() - start,
        )
