"""Thin bridge to the pinned MemoryAgentBench submodule.

Data loading, chunking, prompt templates and scoring all come from the benchmark's own code,
so every method in this repo is fed and scored exactly the way the paper's runs were.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent.parent / "baselines" / "memoryagentbench"
sys.path.insert(0, str(BENCH_DIR))

from conversation_creator import ConversationCreator  # noqa: E402
from utils.eval_data_utils import format_chat  # noqa: E402
from utils.eval_other_utils import normalize_answer, post_process  # noqa: E402
from utils.templates import get_template  # noqa: E402

from baselines.common.protocol import Question, Task  # noqa: E402

__all__ = ["build_task", "score", "answer_in_text", "get_template", "format_chat", "LENGTHS", "SPLITS"]

LENGTHS = ("6k", "32k", "64k", "262k")
SPLITS = ("sh", "mh")


@dataclass
class Gold:
    q_index: int
    split: str
    qa_pair_id: str | None
    answers: list[str]


def _dataset_config(sub_dataset: str, chunk_size: int) -> dict:
    return {"dataset": "Conflict_Resolution", "sub_dataset": sub_dataset, "chunk_size": chunk_size,
            "max_test_samples": 1, "context_max_length": 300000, "seed": 42, "debug": False}


def build_task(length: str, splits: list[str], chunk_size: int, agent_name: str,
               max_questions: int | None) -> tuple[Task, list[Gold]]:
    """Load FactConsolidation at one length for one or both splits.

    SH and MH share the identical context at every length, so one memory serves both: the task
    holds the chunks once and the questions of every requested split. `agent_name` selects the
    benchmark's prompt family ("rag" -> rag_agent, "Long_context_agent", "Agentic_memory").
    `max_questions` keeps the first N questions of each split.
    """
    chunks: list[str] | None = None
    questions: list[Question] = []
    golds: list[Gold] = []
    sub_datasets = [f"factconsolidation_{s}_{length}" for s in splits]
    for split, sub_dataset in zip(splits, sub_datasets):
        creator = ConversationCreator({"agent_name": agent_name}, _dataset_config(sub_dataset, chunk_size))
        split_chunks = creator.get_chunks()[0]  # every FC sub-dataset has exactly one context
        if chunks is None:
            chunks = split_chunks
        elif split_chunks != chunks:
            raise ValueError(f"{sub_dataset} does not share its context with {sub_datasets[0]}")
        pairs = creator.get_query_and_answers()[0]
        for query, answers, qa_pair_id in pairs[:max_questions]:
            q_index = len(questions)
            questions.append(Question(q_index=q_index, split=split, query=query))
            golds.append(Gold(q_index=q_index, split=split, qa_pair_id=qa_pair_id, answers=answers))
    return Task(sub_datasets=sub_datasets, chunk_size=chunk_size, chunks=chunks, questions=questions), golds


def score(prediction: str, answers: list[str]) -> dict[str, float]:
    """Benchmark scoring; FC is reported as `substring_exact_match`."""
    metrics, _ = post_process({"output": prediction}, answers, _dataset_config("factconsolidation_sh_6k", 0))
    return {k: float(v) for k, v in metrics.items()}


def answer_in_text(answers: list[str], text: str) -> bool:
    """Whether any gold answer appears in a method's retrieved memory (the benchmark's normalisation).
    A retrieval-side check: did the answer reach the model at all?"""
    haystack = normalize_answer(text)
    return any(normalize_answer(a) in haystack for a in answers)
