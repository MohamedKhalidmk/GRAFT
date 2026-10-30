"""BM25 baseline, following the benchmark's RAG path step by step.

Source: baselines/memoryagentbench/agent.py, `_handle_rag_agent` (memorize) and
`_handle_bm25_rag` (query). Same retriever (LangChain BM25Retriever), same memorize template,
same retrieval-query extraction and prompt layout. Only the answering LLM is Claude.
"""

import re
import time

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from baselines.claude_llm import ClaudeLLM
from baselines.common.protocol import Gateway, Question, Task, run_agent
from eval.benchmark import format_chat, get_template

AGENT_NAME = "Simple_rag_bm25"  # selects the benchmark's rag_agent prompts


class BM25Agent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.llm = ClaudeLLM(gateway.anthropic_base_url, config["model"])
        self.answer_max_tokens = config["answer_max_tokens"]
        self.retrieve_num = config["retrieve_num"]
        self.sub_dataset = task.sub_datasets[0]
        self.retriever: BM25Retriever | None = None

    def memorize(self, chunks: list[str]) -> dict:
        template = get_template(self.sub_dataset, "memorize", AGENT_NAME)
        memories = [template.format(context=c, time_stamp=time.strftime("%Y-%m-%d %H:%M:%S")) for c in chunks]
        docs = [Document(page_content=t, metadata={"source": "Not provided", "chunk": i})
                for i, t in enumerate(memories)]
        self.retriever = BM25Retriever.from_documents(docs)
        self.retriever.k = self.retrieve_num
        return {}

    def prompt(self, query: str) -> tuple[str, str]:
        """Return (system, user) exactly as the benchmark would send them."""
        retrieved = self.retriever.invoke(retrieval_query(query))
        memory = "\n".join(f"Memory {i + 1}:\n{doc.page_content}\n" for i, doc in enumerate(retrieved))
        chat = format_chat(message=memory + "\n" + query,
                           system_message=get_template(self.sub_dataset, "system", AGENT_NAME))
        return chat[0]["content"], chat[1]["content"]

    def answer(self, question: Question) -> tuple[str, dict]:
        system, user = self.prompt(question.query)
        call = self.llm.complete(system, user, max_tokens=self.answer_max_tokens)
        return call.text, {"stop_reason": call.stop_reason, "retrieved_text": user.rsplit(question.query, 1)[0]}


def retrieval_query(message: str) -> str:
    """Same patterns as agent.py `_extract_retrieval_query`."""
    for pattern in (r"Now Answer the Question:\s*(.*)", r"Here is the conversation:\s*(.*)"):
        match = re.search(pattern, message, re.DOTALL)
        if match:
            return "".join(match.groups())
    return message


if __name__ == "__main__":
    run_agent(BM25Agent)
