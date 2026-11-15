"""GRAFT answer phase: serialize the retrieved region and ask Claude the benchmark's question.

The prompt layout is the benchmark's RAG layout (as BM25 gets it): retrieved memories, then the
benchmark's FactConsolidation query prompt, with the benchmark's system prompt. Each memory is one
fact with its provenance: serial number (or arrival order), source chunk, and the original sentence.
"""

from baselines.claude_llm import ClaudeLLM, LLMCall
from eval.benchmark import format_chat, get_template
from my_method.graph_store import GraphStore
from my_method.retrieval import Region

AGENT_NAME = "Structure_rag_sgar"  # the benchmark's rag_agent prompts


def fact_line(store: GraphStore, fact: str, outdated: bool) -> str:
    d = store.fact(fact)
    prov = d["provenance"]
    text = prov["span"] or f"{d['subject']} {d['relation']} {d['object']}"
    number = prov["serial"] if prov["serial"] is not None else f"arrival {prov['arrival']}"
    line = f"{number}. {text.rstrip('.')}. (source: chunk {prov['chunk_id']})"
    if outdated:
        newer = store.current(fact)
        line += f" [OUTDATED: replaced by fact {store.fact(newer)['provenance']['serial']}]"
    return line


def serialize(store: GraphStore, region: Region) -> str:
    return "\n".join(f"Memory {i + 1}:\n{fact_line(store, f, f in region.outdated)}\n"
                     for i, f in enumerate(region.facts))


def answer(llm: ClaudeLLM, store: GraphStore, region: Region, query: str, sub_dataset: str,
           max_tokens: int) -> tuple[LLMCall, str]:
    memory = serialize(store, region)
    chat = format_chat(message=memory + "\n" + query, system_message=get_template(sub_dataset, "system", AGENT_NAME))
    return llm.complete(chat[0]["content"], chat[1]["content"], max_tokens), memory
