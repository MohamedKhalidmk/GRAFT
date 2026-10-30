"""API cost from token usage, using configs/pricing.yaml."""

from functools import cache
from pathlib import Path

import yaml

PRICING_FILE = Path(__file__).resolve().parent.parent / "configs" / "pricing.yaml"


@cache
def _pricing(model: str) -> dict:
    return yaml.safe_load(PRICING_FILE.read_text())[model]


def token_cost(model: str, input_tokens: int, output_tokens: int,
               cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> float:
    """USD for one request. The rate card depends on the request's total prompt length."""
    p = _pricing(model)
    prompt_tokens = input_tokens + cache_read_tokens + cache_write_tokens
    card = p["long"] if prompt_tokens > p["long_prompt_threshold"] else p["short"]
    usd_per_mtok = (input_tokens * card["input"]
                    + cache_read_tokens * card["input"] * p["cache_read_multiplier"]
                    + cache_write_tokens * card["input"] * p["cache_write_multiplier"]
                    + output_tokens * card["output"])
    return usd_per_mtok / 1e6
