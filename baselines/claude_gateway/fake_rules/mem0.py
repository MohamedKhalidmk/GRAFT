"""Mem0's prompt families (mem0/configs/prompts.py), bundled 0.1.88 and upstream 2.2.1.

- 0.1.88 fact extraction: system FACT_RETRIEVAL_PROMPT, user "Input:\\n<conversation>"
  -> {"facts": [...]}
- 0.1.88 memory update: one user message built by get_update_memory_messages, holding the old
  memories and the new facts as Python reprs in triple backticks -> {"memory": [{id, text, event}]}
- 2.2.1 additive extraction: system ADDITIVE_EXTRACTION_PROMPT, user with "## New Messages"
  -> {"memory": [{id, text}]} (ADD-only pipeline)

Extraction returns the numbered fact sentences of a FactConsolidation chunk. The update reply is
NONE for a fact already stored verbatim, UPDATE for an old memory with the same subject (all words
but the last two), else ADD, so all of Mem0's update paths run.
"""

import ast
import json
import re

from baselines.claude_gateway.fake import FakeReply, FakeRequest

PRIORITY = 20

FACT_RE = re.compile(r"(?<!\S)\d+\.\s+(.+?)(?=\s+\d+\.\s|\n|$)")
BACKTICK_BLOCK_RE = re.compile(r"```\s*\n(.*?)\n\s*```", re.DOTALL)


def rule(request: FakeRequest) -> FakeReply | None:
    user = request.last_user_text
    if "Personal Information Organizer" in request.system and user.startswith("Input:"):
        return _json({"facts": extract_facts(user)})
    if "smart memory manager" in user and "The new retrieved facts" in user:
        return _json({"memory": update_actions(user)})
    if "Memory Extractor" in request.system and "## New Messages" in user:
        new_messages = user.split("## New Messages", 1)[1].split("## Observation Date", 1)[0]
        return _json({"memory": [{"id": str(i), "text": f} for i, f in enumerate(extract_facts(new_messages))]})
    return None


def extract_facts(text: str) -> list[str]:
    return [m.group(1).strip().removesuffix(".") for m in FACT_RE.finditer(text)]


def update_actions(prompt: str) -> list[dict]:
    old_block, new_block = BACKTICK_BLOCK_RE.findall(prompt)[-2:]
    old_memories: list[dict] = ast.literal_eval(old_block.strip())
    new_facts: list[str] = ast.literal_eval(new_block.strip())
    by_text = {m["text"]: m for m in old_memories}
    by_subject = {subject(m["text"]): m for m in old_memories}
    actions, next_id = [], len(old_memories)
    for fact in new_facts:
        if fact in by_text:
            m = by_text[fact]
            actions.append({"id": m["id"], "text": m["text"], "event": "NONE"})
        elif subject(fact) in by_subject:
            m = by_subject.pop(subject(fact))
            actions.append({"id": m["id"], "text": fact, "event": "UPDATE", "old_memory": m["text"]})
        else:
            actions.append({"id": str(next_id), "text": fact, "event": "ADD"})
            next_id += 1
    return actions


def subject(fact: str) -> str:
    return " ".join(fact.lower().split()[:-2])


def _json(payload: dict) -> FakeReply:
    return FakeReply(json.dumps(payload, ensure_ascii=False))
