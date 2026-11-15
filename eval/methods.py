"""Every method the bench can run, with its environment, prompt family and default settings.

`agent_name` is passed to the benchmark's template lookup and decides which query prompt the
method gets ("rag" -> rag_agent, "Long_context_agent", "Agentic_memory" -> agentic_memory_agent),
mirroring the agent_name in the benchmark's own config for that system.
`chunk_size` defaults follow the paper (Appendix F.3): 512 for FC, 4096 for Mem0, Zep, Cognee,
MIRIX (and Letta, per the released config).
`paper_row` names the matching row of the paper's Table 3, for the reference block.
"""

from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class MethodSpec:
    key: str
    display: str
    family: str
    module: str
    env: str  # "core" = .venv, otherwise envs/<env>
    agent_name: str
    chunk_size: int
    defaults: dict = field(default_factory=dict)
    paper_row: str | None = None
    optional: bool = False

    @property
    def python(self) -> Path:
        return REPO / ".venv" / "bin" / "python" if self.env == "core" else REPO / "envs" / self.env / "bin" / "python"


LONG_CONTEXT, SIMPLE_RAG, STRUCTURE_RAG, AGENTIC, OURS = (
    "Long-Context Agents", "Simple RAG Agents", "Structure-Augmented RAG Agents",
    "Agentic Memory Agents", "Ours (structure-augmented + agentic)")

class _Methods(dict):
    """Method table that also accepts old keys (the method was called SGAR during development)."""
    ALIASES = {"sgar": "graft"}

    def __getitem__(self, key):
        return super().__getitem__(self.ALIASES.get(key, key))

    def __contains__(self, key):
        return super().__contains__(self.ALIASES.get(key, key))


METHODS: dict[str, MethodSpec] = _Methods({m.key: m for m in [
    MethodSpec("long_context", "Claude Haiku 5.5 (1M, full history)", LONG_CONTEXT,
               "baselines.long_context.agent", "core", "Long_context_agent", 512,
               {"truncate_to_tokens": None}, paper_row="GPT-4o-mini (128K)"),
    MethodSpec("long_context_128k", "Claude Haiku 5.5 (newest 128K)", LONG_CONTEXT,
               "baselines.long_context.agent", "core", "Long_context_agent", 512,
               {"truncate_to_tokens": 123990}, paper_row="GPT-4o-mini (128K)"),
    MethodSpec("bm25", "BM25", SIMPLE_RAG, "baselines.bm25.agent", "core", "Simple_rag_bm25", 512,
               {"retrieve_num": 10}, paper_row="BM25"),
    MethodSpec("hipporag_bundled", "HippoRAG-v2 (benchmark copy)", STRUCTURE_RAG,
               "baselines.hipporag.agent", "hipporag-bundled", "Structure_rag_hippo_rag_v2", 512,
               {"retrieve_num": 10, "source": "bundled"}, paper_row="HippoRAG-v2"),
    MethodSpec("hipporag_upstream", "HippoRAG-v2 (upstream)", STRUCTURE_RAG,
               "baselines.hipporag.agent", "hipporag-upstream", "Structure_rag_hippo_rag_v2", 512,
               {"retrieve_num": 10, "source": "upstream"}, paper_row="HippoRAG-v2"),
    MethodSpec("mem0_bundled", "Mem0 (benchmark copy)", STRUCTURE_RAG, "baselines.mem0.agent",
               "mem0-bundled", "Structure_rag_mem0", 4096, {"retrieve_num": 100, "source": "bundled"},
               paper_row="Mem0"),
    MethodSpec("mem0_upstream", "Mem0 (upstream)", STRUCTURE_RAG, "baselines.mem0.agent",
               "mem0-upstream", "Structure_rag_mem0", 4096, {"retrieve_num": 100, "source": "upstream"},
               paper_row="Mem0"),
    MethodSpec("letta_bundled", "MemGPT / Letta (benchmark copy)", AGENTIC, "baselines.letta.agent",
               "letta-bundled", "Agentic_memory_letta", 4096, {"source": "bundled"}, paper_row="MemGPT"),
    MethodSpec("letta_upstream", "Letta server 0.16.8 (last MemGPT-lineage release)", AGENTIC, "baselines.letta.agent",
               "letta-upstream", "Agentic_memory_letta", 4096, {"source": "upstream"}, paper_row="MemGPT"),
    MethodSpec("knowl", "Knowl (supersede)", AGENTIC, "baselines.knowl.agent", "knowl",
               "Agentic_memory_knowl", 512, {"retrieve_num": 10, "knowl_supersede": True, "knowl_vector": True},
               optional=True),
    MethodSpec("total_agent_memory", "total-agent-memory (supersede)", AGENTIC,
               "baselines.total_agent_memory.agent", "total-agent-memory",
               "Agentic_memory_total_agent_memory", 512,
               {"retrieve_num": 10, "tam_supersede": True, "tam_show_recorded": True}, optional=True),
    MethodSpec("graft", "GRAFT (ours)", OURS, "my_method.agent", "core", "Structure_rag_sgar", 512, {
        "writer": "llm", "schema": "fixed", "schema_path": "my_method/schema.yaml", "revisions": True,
        "retrieval": "gnn_goat", "gnn_checkpoint": "results/checkpoints/gnn_default",
        # 5120 tokens = what BM25 and HippoRAG hand the model (top 10 chunks of 512 tokens)
        "max_facts": 300, "max_tokens": 5120, "include_outdated": False, "goat_targets": 3, "goat_topk": 12,
        "writer_max_tokens": 8192}),
]})
