"""MemGPT / Letta baseline, following the benchmark's Letta path step by step.

Source: baselines/memoryagentbench/agent.py, `_initialize_letta_agent`, `_handle_letta_agent`,
`_process_letta_message`, `save_agent` / `load_agent`, with the released config
configs/agent_conf/RAG_Agents/gpt-4o-mini/Agentic_memory_gpt-4o-mini-letta.yaml (letta_mode: insert,
system prompt configs/agent_conf/letta_system.txt, agent_chunk_size 4096). Same human/persona
blocks (limit 2,000,000), same memorize template; in insert mode every formatted chunk goes into
archival memory and every question is one user message to the agent, whose `send_message`
argument is the prediction. As in the benchmark, every question starts from the memory state
saved right after memorization.

config["source"] selects the Letta version:
  bundled   the Letta 0.7.0 copy inside the benchmark (the paper's MemGPT runs), in process via
            `create_client()`, exactly as the benchmark calls it.
  upstream  the last release of the Letta (MemGPT) server, 0.16.8; PyPI `letta` 0.32+ is Letta
            Code, a different product. It needs Postgres + pgvector (SQLite support was removed in
            0.12), so this module starts a throwaway Postgres (the `pgserver` wheel's binaries) and
            `letta server` as subprocesses inside work_dir, talks to them with `letta-client`, and
            stops both at exit.

Deviations from the benchmark, and why:
  - LLM: Letta's OpenAI endpoint type pointed at the gateway (dummy key), which answers with
    Claude. Letta's Anthropic provider is not used: it sends parameters current Claude models
    reject, while the gateway translates every request uniformly. The Letta-side config is the
    benchmark's `LLMConfig.default_config("gpt-4o-mini")` with only the endpoint changed: model
    name gpt-4o-mini (so Letta builds the same requests and counts tokens with the same tokenizer),
    context_window 128000 (gpt-4o-mini's, which decides when Letta summarizes; Claude's larger
    window is not used, to keep the paper's memory pressure), max_tokens 4096 (Letta's default).
    config["answer_max_tokens"] is not applied: every Letta step is a tool call carrying inner
    thoughts, so a 16-token cap would truncate the call, and the benchmark had no such cap.
  - Embeddings: Letta's OpenAI embedding endpoint type pointed at the gateway, with the run's
    shared embedding model (config["embedding_model"]) instead of text-embedding-3-small; the
    dimension is probed from the gateway. embedding_chunk_size stays 2 x chunk size.
  - State lives in config["work_dir"] (HOME and LETTA_DIR point there), never in ~/.letta. The
    bundled save/load copies sqlite.db to and from work_dir/saved_agent as the benchmark does.
  - upstream: agent_type memgpt_agent (the original MemGPT loop with send_message and heartbeats,
    which the benchmark's system prompt describes; 0.16.8 defaults to letta_v1_agent), with its
    default tools plus archival_memory_insert / archival_memory_search, which 0.16.8 marks
    deprecated and no longer attaches by default; without them the agent could not read the
    archival memory the benchmark fills. Archival inserts use `agents.passages.create`. Instead of copying a database file, each question
    restores the saved state through the API: messages reset to the initial sequence, memory
    blocks restored, archival passages added after memorization deleted. The prediction is
    the `message` argument of the last send_message call (the benchmark indexes messages[-3],
    which points at that call only in 0.7.0's response layout).
  - The benchmark turns any exception during a question into the prediction "Error"; we keep
    that, and record the exception in predictions.jsonl.
"""

import atexit
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from baselines.common.protocol import Gateway, Question, Task, run_agent

REPO = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO / "baselines" / "memoryagentbench"
AGENT_NAME = "Agentic_memory_letta"
SYSTEM_PROMPT = BENCH_DIR / "configs" / "agent_conf" / "letta_system.txt"
HUMAN = "User is sharing the contents they are reading recently."
PERSONA = "You are a helpful assistant that can help memorize details in the conversation."
BLOCK_LIMIT = 2000000
LETTA_MODEL = "gpt-4o-mini"  # the benchmark's Letta model; the gateway replaces it with Claude
CONTEXT_WINDOW = 128000  # LLMConfig.default_config("gpt-4o-mini")
MAX_TOKENS = 4096
DUMMY_KEY = "sk-gateway-dummy"
ARCHIVAL_TOOLS = ["archival_memory_insert", "archival_memory_search"]  # base tools in 0.7.0, opt-in in 0.16.8
MIGRATIONS = Path(sys.prefix) / "letta-migrations"  # alembic/ from the 0.16.8 sdist, see scripts/setup


def _load_templates():
    """The benchmark's utils/templates.py, by path (its top-level `utils` would shadow others)."""
    spec = importlib.util.spec_from_file_location("bench_templates", BENCH_DIR / "utils" / "templates.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def memorize_messages(sub_dataset: str, chunks: list[str]) -> list[str]:
    template = _load_templates().get_template(sub_dataset, "memorize", AGENT_NAME)
    stamp = {"time_stamp": time.strftime("%Y-%m-%d %H:%M:%S")} if "{time_stamp}" in template else {}
    return [template.format(context=c, **stamp) for c in chunks]


def isolate_state(work_dir: Path, gateway: Gateway) -> dict:
    """Point Letta's home, data dir and OpenAI settings at work_dir and the gateway (before importing letta)."""
    work_dir.mkdir(parents=True, exist_ok=True)
    env = {"HOME": str(work_dir), "LETTA_DIR": str(work_dir / ".letta"), "OPENAI_API_KEY": DUMMY_KEY,
           "OPENAI_API_BASE": gateway.openai_base_url, "OPENAI_BASE_URL": gateway.openai_base_url}
    os.environ.update(env)
    return env


def embedding_dim(gateway: Gateway, model: str) -> int:
    body = json.dumps({"input": ["probe"], "model": model}).encode()
    request = urllib.request.Request(gateway.openai_base_url + "/embeddings", data=body,
                                     headers={"Content-Type": "application/json"})
    return len(json.loads(urllib.request.urlopen(request, timeout=60).read())["data"][0]["embedding"])


def llm_config(gateway: Gateway) -> dict:
    return {"model": LETTA_MODEL, "model_endpoint_type": "openai", "model_endpoint": gateway.openai_base_url,
            "model_wrapper": None, "context_window": CONTEXT_WINDOW, "put_inner_thoughts_in_kwargs": True,
            "max_tokens": MAX_TOKENS}


def embedding_config(gateway: Gateway, config: dict, task: Task) -> dict:
    return {"embedding_model": config["embedding_model"], "embedding_endpoint_type": "openai",
            "embedding_endpoint": gateway.openai_base_url,
            "embedding_dim": embedding_dim(gateway, config["embedding_model"]),
            "embedding_chunk_size": task.chunk_size * 2}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BundledLetta:
    """Letta 0.7.0 from the benchmark, in process, as `_initialize_letta_agent` sets it up."""

    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.work_dir = Path(config["work_dir"])
        isolate_state(self.work_dir, gateway)
        sys.path.append(str(BENCH_DIR))  # appended, so the benchmark's `utils`, `mem0`... never shadow
        from letta import BasicBlockMemory, EmbeddingConfig, LLMConfig, create_client

        self.sub_dataset = task.sub_datasets[0]
        self.save_dir = self.work_dir / "saved_agent"
        self.db_path = self.work_dir / ".letta" / "sqlite.db"
        self.client = create_client()
        self.client.set_default_llm_config(LLMConfig(**llm_config(gateway)))
        self.client.set_default_embedding_config(EmbeddingConfig(**embedding_config(gateway, config, task)))
        human = self.client.create_block(label="human", value=HUMAN, limit=BLOCK_LIMIT)
        persona = self.client.create_block(label="persona", value=PERSONA, limit=BLOCK_LIMIT)
        self.agent_state = self.client.create_agent(name="mm_agent", memory=BasicBlockMemory(blocks=[human, persona]),
                                                    system=SYSTEM_PROMPT.read_text())

    def memorize(self, chunks: list[str]) -> dict:
        passages = 0
        for text in memorize_messages(self.sub_dataset, chunks):
            passages += len(self.client.server.passage_manager.insert_passage(
                agent_state=self.agent_state, agent_id=self.agent_state.id, text=text, actor=self.client.user))
        self.save_agent()
        return {"archival_passages": passages, "letta_version": "0.7.0 (bundled)",
                "embedding_dim": self.agent_state.embedding_config.embedding_dim}

    def save_agent(self) -> None:
        self.save_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.db_path, self.save_dir / "sqlite.db")
        (self.save_dir / "agent_id.txt").write_text(self.agent_state.id)

    def load_agent(self) -> None:
        shutil.copyfile(self.save_dir / "sqlite.db", self.db_path)
        agent_id = (self.save_dir / "agent_id.txt").read_text()
        self.agent_state = next(a for a in self.client.list_agents() if a.id == agent_id)

    def answer(self, question: Question) -> tuple[str, dict]:
        self.load_agent()
        try:
            response = self.client.send_message(agent_id=self.agent_state.id, message=question.query, role="user")
            return json.loads(response.messages[-3].tool_call.arguments)["message"], {"steps": len(response.messages)}
        except Exception as e:  # the benchmark answers "Error" for any failure
            print(f"[letta] q{question.q_index} failed: {type(e).__name__}: {e}", flush=True)
            return "Error", {"error": f"{type(e).__name__}: {e}"}


class Postgres:
    """A throwaway Postgres 16 + pgvector from the `pgserver` wheel, on a local TCP port."""

    def __init__(self, data_dir: Path):
        from pgserver._commands import POSTGRES_BIN_PATH

        self.bin = POSTGRES_BIN_PATH
        self.data_dir = data_dir
        self.port = free_port()
        subprocess.run([self.bin / "initdb", "-D", data_dir, "-U", "postgres", "--auth=trust", "-E", "UTF8"],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run([self.bin / "pg_ctl", "-D", data_dir, "-w", "-l", data_dir / "postgres.log",
                        "-o", f"-h 127.0.0.1 -p {self.port} -c unix_socket_directories=''", "start"],
                       check=True, stdout=subprocess.DEVNULL)
        self.uri = f"postgresql://postgres@127.0.0.1:{self.port}/postgres"

    def stop(self) -> None:
        subprocess.run([self.bin / "pg_ctl", "-D", self.data_dir, "-m", "fast", "-w", "stop"],
                       stdout=subprocess.DEVNULL, check=False)


def migrate(postgres: Postgres, env: dict) -> None:
    """Create Letta's schema the way its Docker image does: pgvector, then `alembic upgrade head`."""
    subprocess.run([postgres.bin / "psql", "-h", "127.0.0.1", "-p", str(postgres.port), "-U", "postgres",
                    "-q", "-c", "CREATE EXTENSION IF NOT EXISTS vector"], check=True)
    subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=MIGRATIONS,
                   env={**os.environ, **env, "LETTA_PG_URI": postgres.uri}, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class LettaServer:
    """`letta server` from this environment, as a subprocess with its log in work_dir."""

    def __init__(self, work_dir: Path, env: dict):
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.log_path = work_dir / "letta_server.log"
        letta_bin = Path(sys.executable).parent / "letta"
        self.proc = subprocess.Popen([letta_bin, "server", "--host", "127.0.0.1", "--port", str(self.port)],
                                     env={**os.environ, **env},
                                     stdout=open(self.log_path, "w"), stderr=subprocess.STDOUT)
        self._wait_ready()

    def _wait_ready(self) -> None:
        for _ in range(600):
            if self.proc.poll() is not None:
                raise RuntimeError(f"letta server exited; see {self.log_path}")
            try:
                urllib.request.urlopen(self.url + "/v1/health/", timeout=1)
                return
            except OSError:
                time.sleep(0.5)
        raise RuntimeError(f"letta server did not start within 5 minutes; see {self.log_path}")

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()


class UpstreamLetta:
    """Letta 0.16.8 server: the same agent, memory and messages through the REST API."""

    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.work_dir = Path(config["work_dir"])
        env = isolate_state(self.work_dir, gateway)
        self.sub_dataset = task.sub_datasets[0]
        self.postgres = Postgres(self.work_dir / "pgdata")
        # the server's asyncpg engine requires SSL unless the URI says otherwise (pg8000, used by
        # alembic, rejects that parameter, so only the server gets it)
        env["LETTA_PG_URI"] = self.postgres.uri + "?ssl=disable"
        self.server: LettaServer | None = None
        try:
            migrate(self.postgres, env)
            self.server = LettaServer(self.work_dir, env)
            from letta_client import Letta

            self.client = Letta(base_url=self.server.url, timeout=600)
            self.agent = self.client.agents.create(
                name="mm_agent", agent_type="memgpt_agent", system=SYSTEM_PROMPT.read_text(), tools=ARCHIVAL_TOOLS,
                memory_blocks=[{"label": "human", "value": HUMAN, "limit": BLOCK_LIMIT},
                               {"label": "persona", "value": PERSONA, "limit": BLOCK_LIMIT}],
                llm_config=llm_config(gateway), embedding_config=embedding_config(gateway, config, task))
        except BaseException:
            self.close()
            raise
        self.saved_blocks: dict[str, str] = {}
        self.saved_passages: set[str] = set()

    def close(self) -> None:
        if self.server:
            self.server.stop()
        self.postgres.stop()

    def memorize(self, chunks: list[str]) -> dict:
        for text in memorize_messages(self.sub_dataset, chunks):
            self.client.agents.passages.create(self.agent.id, text=text)
        self.saved_blocks = {b.label: b.value for b in self.client.agents.blocks.list(self.agent.id)}
        self.saved_passages = self._passage_ids()
        return {"archival_passages": len(self.saved_passages), "letta_version": "0.16.8 (upstream server)",
                "embedding_dim": self.agent.embedding_config.embedding_dim}

    def _passage_ids(self) -> set[str]:
        return {p.id for p in self.client.agents.passages.list(self.agent.id, limit=100000)}

    def load_agent(self) -> None:
        """Restore the state saved after memorization (the benchmark copies the database back)."""
        self.client.agents.messages.reset(self.agent.id, add_default_initial_messages=True)
        for label, value in self.saved_blocks.items():
            self.client.agents.blocks.update(label, agent_id=self.agent.id, value=value)
        for passage_id in self._passage_ids() - self.saved_passages:
            self.client.agents.passages.delete(passage_id, agent_id=self.agent.id)

    def answer(self, question: Question) -> tuple[str, dict]:
        self.load_agent()
        try:
            response = self.client.agents.messages.create(
                self.agent.id, messages=[{"role": "user", "content": question.query}], use_assistant_message=False)
            calls = [m.tool_call for m in response.messages
                     if m.message_type == "tool_call_message" and m.tool_call.name == "send_message"]
            return json.loads(calls[-1].arguments)["message"], {"steps": len(response.messages)}
        except Exception as e:  # the benchmark answers "Error" for any failure
            print(f"[letta] q{question.q_index} failed: {type(e).__name__}: {e}", flush=True)
            return "Error", {"error": f"{type(e).__name__}: {e}"}


def make_agent(config: dict, gateway: Gateway, task: Task):
    if config["source"] == "bundled":
        return BundledLetta(config, gateway, task)
    agent = UpstreamLetta(config, gateway, task)
    atexit.register(agent.close)
    return agent


if __name__ == "__main__":
    run_agent(make_agent)
