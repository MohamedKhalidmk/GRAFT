"""Long-context baseline: Claude reads the whole memorized history with every question.

Follows the benchmark's agent.py `_handle_long_context_agent` / `_query_long_context_agent`:
each chunk is wrapped in the benchmark's memorize template and appended to one context string;
a question is answered from `context + "\\n" + query`.

`truncate_to_tokens` reproduces the paper's GPT-4o-mini setting, which kept only the newest
123,990 tokens (128K limit - 4K buffer - 10 output; counted with GPT-4o-mini's tokenizer,
as the benchmark does). Leave it null to give Claude the full history (Haiku 5.5 has 1M).

The history is marked for prompt caching: every question shares it, so after the first question
it is billed at the cache-read rate. Caching does not change what the model sees.
"""

import time

import tiktoken

from baselines.claude_llm import ClaudeLLM
from baselines.common.protocol import Gateway, Question, Task, run_agent
from eval.benchmark import get_template

AGENT_NAME = "Long_context_agent"  # selects the benchmark's long_context_agent prompts


class LongContextAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.llm = ClaudeLLM(gateway.anthropic_base_url, config["model"])
        self.answer_max_tokens = config["answer_max_tokens"]
        self.truncate_to_tokens = config.get("truncate_to_tokens")
        self.sub_dataset = task.sub_datasets[0]
        self.context = ""

    def memorize(self, chunks: list[str]) -> dict:
        template = get_template(self.sub_dataset, "memorize", AGENT_NAME)
        for chunk in chunks:
            wrapped = template.format(context=chunk, time_stamp=time.strftime("%Y-%m-%d %H:%M:%S"))
            self.context = (self.context + "\n" + wrapped).strip()
        tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = tokenizer.encode(self.context, disallowed_special=())
        truncated = self.truncate_to_tokens is not None and len(tokens) > self.truncate_to_tokens
        if truncated:  # keep the newest tokens, as the benchmark's FIFO eviction does
            self.context = tokenizer.decode(tokens[-self.truncate_to_tokens:])
        return {"history_tokens_gpt4o": len(tokens), "truncated": truncated,
                "kept_tokens_gpt4o": min(len(tokens), self.truncate_to_tokens or len(tokens))}

    def answer(self, question: Question) -> tuple[str, dict]:
        system = get_template(self.sub_dataset, "system", AGENT_NAME)
        user = [{"type": "text", "text": self.context, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "\n" + question.query}]
        call = self.llm.complete(system, user, self.answer_max_tokens)
        return call.text, {"stop_reason": call.stop_reason}


if __name__ == "__main__":
    run_agent(LongContextAgent)
