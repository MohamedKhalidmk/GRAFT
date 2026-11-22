# Sources: knowl, total-agent-memory, memoryagentbench (docs/reference/REFERENCES.md)
"""Drive the benchmark's own `methods/*.py` handlers without its heavy agent.py.

The Knowl and total-agent-memory handlers (`initialize_*_agent`, `handle_*_agent`) take the
benchmark's AgentWrapper and read a handful of attributes from it. `BenchAgent` is a stand-in
with exactly those attributes, so the handler code runs unmodified; only the reader's client
points at the Claude gateway.
"""

import re
import sys
from pathlib import Path

from openai import OpenAI

from baselines.common.protocol import Gateway

BENCH_DIR = Path(__file__).resolve().parents[1] / "memoryagentbench"
sys.path.insert(0, str(BENCH_DIR))  # the handlers import `methods.*` and `utils.templates`

# The published configs' reader model. The gateway ignores the name and answers with Claude, but
# the handlers only pass `max_tokens` when "gpt-4" is in it, and the bench caps answers at
# `answer_max_tokens`.
BENCH_MODEL = "gpt-4o-mini"
BENCH_TEMPERATURE = 0.7  # published configs; the gateway drops it (Claude rejects sampling params)


class BenchAgent:
    """The subset of the benchmark's AgentWrapper that the memory-method handlers touch."""

    def __init__(self, agent_name: str, sub_dataset: str, gateway: Gateway, answer_max_tokens: int):
        self.agent_name = agent_name
        self.sub_dataset = sub_dataset
        self.model = BENCH_MODEL
        self.temperature = BENCH_TEMPERATURE
        self.max_tokens = answer_max_tokens
        self.client = OpenAI(base_url=gateway.openai_base_url, api_key="via-gateway")

    def _create_oai_client(self) -> OpenAI:
        return self.client

    def _extract_retrieval_query(self, message: str) -> str:
        """Same patterns as agent.py `_extract_retrieval_query`."""
        for pattern in (r"Now Answer the Question:\s*(.*)", r"Here is the conversation:\s*(.*)"):
            match = re.search(pattern, message, re.DOTALL)
            if match:
                return "".join(match.groups())
        return message

    def _create_standard_response(self, output: str, input_len: int, output_len: int,
                                  memory_construction_time: float, query_time_len: float) -> dict:
        return {"output": output, "input_len": input_len, "output_len": output_len,
                "memory_construction_time": memory_construction_time, "query_time_len": query_time_len}
