"""GRAFT working memory: answer in steps and keep the work in the graph (design: docs/design/graft_working_memory_design.md).

Per question:
  1. Plan: the question layer's parse (agent.parse_question_graph) gives a chain of edges with unknowns ?A, ?B ...;
     each edge is one step (at most `max_steps`). No usable parse -> one step, the whole question.
  2. Each step: retrieve (mode C as configured), ask for the step's result as JSON {result, facts, note}, write the
     result, its note and the facts it cited into the graph as a "work" layer linked to the question and the steps.
       mode "graph"       (arm C)  the work layer is in the graph while the question is answered: each step's
                                   retrieval is seeded from the step's subject (the question entity, or the entity the
                                   previous result links to) plus every fact cited so far, and the PageRank walk passes
                                   through the work nodes
       mode "prompt_only" (arm C-) the same steps and calls, but nothing is written to the graph: every step reads the
                                   question's own region, and the chain lives only in the prompt
  3. Final: the benchmark's answer prompt with the working memory chain and the facts cited across the steps.
The work layer is removed after each question and saved whole to work_dir/working_memory.jsonl.
"""

import json
import re

from baselines.claude_llm import ClaudeLLM
from eval.benchmark import format_chat, get_template
from my_method.answer import AGENT_NAME, fact_line
from my_method.graph_store import GraphStore, entity_id, is_stopword_name
from my_method.retrieval import Region, Retriever

STEP_PROMPT_V1 = """GRAFT-STEP
You answer ONE step of a multi-step question, using only the numbered facts given. The working memory shows the
question and the steps already done. Return JSON only:
{"result": "<the entity or value this step asks for, or unknown>", "facts": [<numbers of the facts you used>],
 "note": "<at most 40 words: why>"}"""
# v2 (test 05 run-02): round 1's traces showed steps picking the older of two conflicting facts; the benchmark's answer
# prompt tells the final call that the newer fact wins, the step prompt did not
STEP_PROMPT_V2 = STEP_PROMPT_V1.replace(
    "The working memory shows the\nquestion and the steps already done.",
    "The working memory shows the\nquestion and the steps already done. Facts are numbered in the order they were "
    "stated: if two facts give\ndifferent values for the same thing, the one with the larger number is newer and is "
    "the one that counts.")
STEP_PROMPTS = {"v1": STEP_PROMPT_V1, "v2": STEP_PROMPT_V2}


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


class WorkingMemory:
    def __init__(self, store: GraphStore, retriever: Retriever, llm: ClaudeLLM, mode: str = "graph",
                 max_steps: int = 4, step_max_tokens: int = 256, step_prompt: str = "v1"):
        assert mode in ("graph", "prompt_only"), mode
        self.store, self.retriever, self.llm = store, retriever, llm
        self.mode, self.max_steps, self.step_max_tokens = mode, max_steps, step_max_tokens
        self.step_prompt = STEP_PROMPTS[step_prompt]

    # ---- the work layer ----

    def _add(self, node: str, **attrs) -> None:
        attrs.setdefault("query", True)  # never retrieved as a stored fact (Retriever._is_fact skips query nodes)
        self.store.g.add_node(node, layer="work", **attrs)
        self.store.simple_graph().add_node(node, layer="work", **attrs)
        self.added.append(node)

    def _link(self, a: str, b: str, kind: str) -> None:
        if a in self.store.g and b in self.store.g:
            self.store.g.add_edge(a, b, type=kind)
            self.store.simple_graph().add_edge(a, b)
            self.edges.append((a, kind, b))

    def _clear(self) -> None:
        self.store.g.remove_nodes_from(self.added)
        if self.store._simple is not None:
            self.store._simple.remove_nodes_from(self.added)

    def _entity(self, name: str) -> str | None:
        """A graph entity for a name: exact name first, then the question layer's embedding match."""
        if not name or name.lower() == "unknown" or is_stopword_name(name):
            return None
        e = entity_id(name)
        if e in self.store.g and self.store.fact(e)["type"] == "Entity":
            return e
        try:
            return self.retriever._match_entity(name)
        except Exception:
            return None

    # ---- one question ----

    def _steps(self, question: str, edges: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        return list(edges[: self.max_steps]) if edges else [(question, "answer", "?A")]

    def _memory_text(self, question: str, done: list[dict]) -> str:
        lines = ["[Working memory]", f"Question: {question}"]
        for i, d in enumerate(done, 1):
            cited = ", ".join(str(n) for n in d["cited_numbers"]) or "none"
            lines.append(f"Step {i}: {d['text']} -> {d['result']} (facts {cited}). Note: {d['note']}")
        return "\n".join(lines)

    def _facts_block(self, facts: list[str]) -> tuple[str, dict[str, str]]:
        number = {}
        lines = []
        for f in facts:
            prov = self.store.fact(f)["provenance"]
            n = str(prov["serial"] if prov["serial"] is not None else f"arrival {prov['arrival']}")
            number[n] = f
            lines.append(fact_line(self.store, f, False))
        return "\n".join(lines), number

    def run(self, question: str, query: str, edges: list[tuple[str, str, str]], sub_dataset: str,
            answer_max_tokens: int) -> tuple[str, dict]:
        self.added, self.edges = [], []
        steps = self._steps(question, edges)
        value: dict[str, str] = {}  # placeholder -> result text
        node_of: dict[str, str] = {}  # placeholder -> graph entity the result links to
        done, cited, calls = [], [], 0
        base_region = None
        try:
            if self.mode == "graph":
                self._add("W:q", type="Work", kind="question", text=question)
            for i, (s, r, o) in enumerate(steps, 1):
                subj = value.get(s, s) if s.startswith("?") else s
                obj = value.get(o, o) if o.startswith("?") else o
                text = f"{subj} | {r} | {obj}" if r != "answer" else question
                about = node_of.get(s) if s.startswith("?") else self._entity(s)
                if self.mode == "graph":
                    sn = f"W:s{i}"
                    self._add(sn, type="Work", kind="step", text=text)
                    self._link("W:q", sn, "has_step")
                    if i > 1:
                        self._link(f"W:s{i - 1}", sn, "next")
                    if about:
                        self._link(sn, about, "about")
                    if s.startswith("?") and f"W:r{i - 1}" in self.store.g:
                        self._link(sn, f"W:r{i - 1}", "about")
                    seeds = [x for x in [about, sn] + cited if x]
                    region = self.retriever._retrieve(text, extra_seeds=seeds, extra_entities=[about] if about else [])
                else:
                    if base_region is None:
                        base_region = self.retriever._retrieve(question)
                    region = base_region
                block, number = self._facts_block(region.facts)
                prompt = f"{self._memory_text(question, done)}\n\n[Facts]\n{block}\n\n[Step {i}] Find {text}"
                call = self.llm.complete(self.step_prompt, prompt, self.step_max_tokens)
                calls += 1
                rep = _json(call.text)
                result = str(rep.get("result") or "unknown").strip()
                nums = [str(n) for n in rep.get("facts", []) if str(n) in number]
                used = [number[n] for n in nums]
                note = " ".join(str(rep.get("note", "")).split()[:40])
                cited += [f for f in used if f not in cited]
                for ph in (o, s):
                    if ph.startswith("?") and ph not in value:
                        value[ph] = result
                        link = self._entity(result)
                        if link:
                            node_of[ph] = link
                        break
                if self.mode == "graph":
                    rn, nn = f"W:r{i}", f"W:n{i}"
                    self._add(rn, type="Work", kind="result", text=result)
                    self._add(nn, type="Work", kind="note", text=note)
                    self._link(f"W:s{i}", rn, "answer")
                    self._link(f"W:s{i}", nn, "note")
                    for f in used:
                        self._link(f"W:s{i}", f, "used_fact")
                    link = self._entity(result)
                    if link:
                        self._link(rn, link, "same_as")
                done.append({"text": text, "result": result, "cited_numbers": nums, "cited": used, "note": note,
                             "region_facts": len(region.facts), "about": about})
            # final answer: the chain, then the cited facts (latest versions), then the benchmark's query
            final_facts = list(dict.fromkeys(self.store.current(f) for f in cited)) or (done and region.facts) or []
            facts_text = "\n".join(f"Memory {k + 1}:\n{fact_line(self.store, f, False)}\n" for k, f in enumerate(final_facts))
            memory = self._memory_text(question, done) + "\n\n" + facts_text
            chat = format_chat(message=memory + "\n" + query, system_message=get_template(sub_dataset, "system", AGENT_NAME))
            final = self.llm.complete(chat[0]["content"], chat[1]["content"], answer_max_tokens)
            calls += 1
            record = {"question": question, "mode": self.mode, "steps": done, "final_facts": final_facts,
                      "work_nodes": list(self.added), "work_edges": self.edges, "calls": calls}
            return final.text, {"stop_reason": final.stop_reason, "retrieved_text": memory, "working_memory": record,
                                "region_facts": len(final_facts), "steps": len(done), "wm_calls": calls}
        finally:
            self._clear()
