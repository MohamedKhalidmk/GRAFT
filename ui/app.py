"""SGAR control panel.

    .venv/bin/streamlit run ui/app.py

Tabs:
    Run      tick methods and SGAR variants, set data and LLM mode, estimate cost, run a queue, watch logs
    Train    train the GNN (synthetic / SubgraphRAG data) with a live loss and validation chart
    Results  the results table (ours + the paper's reference block) for any length and LLM mode
    Runs     every saved run with its exact config; re-run any of them

Real (paid) runs need ANTHROPIC_API_KEY in the environment Streamlit was started from, a fake-mode
cost estimate of exactly the same selection, and an explicit approval tick.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from eval.benchmark import LENGTHS  # noqa: E402
from eval.methods import METHODS, OURS  # noqa: E402
from eval.queue import queues_dir  # noqa: E402
from eval.table import build as build_table  # noqa: E402
from eval.table import results_dir  # noqa: E402

PYTHON = str(REPO / ".venv" / "bin" / "python")
MODEL = "claude-haiku-5-5"
EMBEDDINGS = ["hash:384", "BAAI/bge-small-en-v1.5", "Qwen/Qwen3-Embedding-0.6B"]
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif'

st.set_page_config(page_title="SGAR test bench", layout="wide")
st.markdown(f"""<style>
html, body, [class*="css"], .stApp, .stMarkdown, .stButton button, table, th, td, code, pre {{
    font-family: {FONT} !important; }}
.stApp {{ background-color: #F5F5F5; color: #303841; }}
.sgar-topbar {{ display: flex; align-items: center; justify-content: space-between; background: #FFFFFF;
    border: 1px solid #E5E5E5; border-radius: 10px; padding: 14px 24px; margin-bottom: 16px; }}
.sgar-topbar .brand {{ font-weight: 700; font-size: 20px; }}
.sgar-topbar .mode-fake {{ color: #1E7B4F; font-weight: 600; }}
.sgar-topbar .mode-real {{ color: #FF5722; font-weight: 700; }}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------- helpers

def env_ready(method: str) -> bool:
    return METHODS[method].python.exists()


def checkpoints() -> list[str]:
    root = results_dir() / "checkpoints"
    return sorted(str(p.parent.relative_to(REPO)) for p in root.glob("*/model.pt")) if root.exists() else []


def make_config(method: str, overrides: dict, length: str, max_questions: int | None, repeats: int,
                mode: str, embedding: str, answer_cap: int, tag: str) -> dict:
    variant = "_".join(f"{k}-{v}" for k, v in sorted(overrides.items()) if k != "gnn_checkpoint")
    return {"run_name": f"{tag}_{method}{'_' + variant if variant else ''}_{length}_{mode}",
            "method": method, "method_config": overrides,
            "data": {"length": length, "splits": ["sh", "mh"], "max_questions": max_questions},
            "llm": {"model": MODEL, "mode": mode, "answer_max_tokens": answer_cap},
            "embedding_model": embedding, "repeats": repeats}


def selection_key(configs: list[dict]) -> str:
    """Identifies a selection independent of mode and run names (to match an estimate to a run)."""
    stripped = [{**c, "run_name": "", "llm": {**c["llm"], "mode": ""}} for c in configs]
    return hashlib.sha1(json.dumps(stripped, sort_keys=True).encode()).hexdigest()[:12]


def launch_queue(configs: list[dict], name: str) -> None:
    folder = REPO / "configs" / "runs" / "ui"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for cfg in configs:
        path = folder / f"{name}_{cfg['run_name']}.yaml"
        path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        paths.append(str(path))
    log = open(queues_dir() / f"{name}.out", "w")
    subprocess.Popen([PYTHON, "-m", "eval.queue", "--name", name, *paths], cwd=REPO, stdout=log,
                     stderr=subprocess.STDOUT, env={**os.environ, "PYTHONPATH": str(REPO)}, start_new_session=True)


def queue_events(name: str) -> list[dict]:
    path = queues_dir() / f"{name}.jsonl"
    return [json.loads(line) for line in open(path)] if path.exists() else []


def queue_done(name: str) -> bool:
    return any(e["status"] == "done" for e in queue_events(name))


def tail(path: Path, lines: int = 40) -> str:
    return "\n".join(path.read_text(errors="replace").splitlines()[-lines:]) if path.exists() else ""


def queue_cost(name: str) -> float:
    total = 0.0
    for e in queue_events(name):
        if e["status"] == "finished":
            total += json.loads((Path(e["run_dir"]) / "summary.json").read_text())["api_cost_usd"]["total"]
    return total


# ---------------------------------------------------------------------------- run tab

def sgar_variant_form() -> None:
    st.markdown("**SGAR variants** (add as many as you want to compare)")
    defaults = METHODS["sgar"].defaults
    c1, c2, c3 = st.columns(3)
    writer = c1.selectbox("Writer", ["llm", "rule"], help="rule = FactConsolidation template parser (ablation)")
    schema = c1.selectbox("Schema", ["fixed", "free"], disabled=writer == "rule")
    revisions = c2.toggle("Revision edges (SUPERSEDES)", value=True)
    retrieval = c2.selectbox("Retrieval", ["gnn_goat", "gnn_topk", "ppr"],
                             help="gnn_goat: trained GNN + GOAt; gnn_topk: GNN top-k nodes; ppr: no GNN")
    ckpts = checkpoints()
    checkpoint = c3.selectbox("GNN checkpoint", ckpts or ["(none: train one in the Train tab)"],
                              disabled=retrieval == "ppr")
    max_facts = c3.number_input("Max facts fetched", 1, 2000, defaults["max_facts"])
    max_tokens = c3.number_input("Max tokens fetched", 100, 20000, defaults["max_tokens"], step=100)
    include_outdated = c2.toggle("Also show outdated versions", value=False)
    if st.button("Add this SGAR variant"):
        variant = {k: v for k, v in {
            "writer": writer, "schema": schema, "revisions": revisions, "retrieval": retrieval,
            "max_facts": int(max_facts), "max_tokens": int(max_tokens), "include_outdated": include_outdated,
            "gnn_checkpoint": checkpoint if retrieval != "ppr" else defaults["gnn_checkpoint"],
        }.items() if v != defaults.get(k)}
        if retrieval != "ppr" and not ckpts:
            st.error("This retrieval mode needs a trained GNN checkpoint. Train one in the Train tab.")
        elif variant not in st.session_state.variants:
            st.session_state.variants.append(variant)
    for i, v in enumerate(st.session_state.variants):
        cols = st.columns([6, 1])
        cols[0].code(json.dumps(v) if v else "defaults (llm writer, fixed schema, revisions, gnn_goat)")
        if cols[1].button("Remove", key=f"rm{i}"):
            st.session_state.variants.pop(i)
            st.rerun()


def run_tab() -> None:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Data and model")
        length = st.selectbox("FactConsolidation length", LENGTHS, index=LENGTHS.index("6k"))
        all_q = st.toggle("All 100 questions per split", value=False)
        max_q = None if all_q else st.number_input("Questions per split", 1, 100, 5)
        repeats = st.number_input("Repeats", 1, 10, 1)
        embedding = st.selectbox("Shared embedding model", EMBEDDINGS,
                                 help="hash:384 needs no download and is for offline tests only")
        answer_cap = st.number_input("Answer cap (Claude tokens)", 4, 256, 16)
        mode = st.radio("LLM", ["fake", "real"], horizontal=True,
                        format_func=lambda m: "Fake (offline, free)" if m == "fake" else "Real Claude Haiku 5.5 (paid)")
    with right:
        st.subheader("Baselines")
        chosen = []
        for key, spec in METHODS.items():
            if spec.family == OURS:
                continue
            ready = env_ready(key)
            label = f"{spec.display}  ·  {spec.family}" + ("  ·  optional" if spec.optional else "")
            if st.checkbox(label, key=f"m_{key}", disabled=not ready,
                           help=None if ready else f"environment missing: run scripts/setup/{spec.env}.sh"):
                chosen.append(key)
    st.divider()
    sgar_variant_form()

    configs = [make_config(m, {}, length, max_q, repeats, mode, embedding, answer_cap, "ui") for m in chosen]
    configs += [make_config("sgar", v, length, max_q, repeats, mode, embedding, answer_cap, "ui")
                for v in st.session_state.variants]
    st.divider()
    st.subheader(f"Queue: {len(configs)} run(s)")
    if not configs:
        st.info("Tick at least one baseline or add an SGAR variant.")
        return
    key = selection_key(configs)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    if mode == "fake":
        if st.button("Run (fake, free)", type="primary"):
            st.session_state.active_queue = f"fake_{stamp}"
            launch_queue(configs, st.session_state.active_queue)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set in the environment this UI was started from.")
        return
    estimate = st.session_state.estimates.get(key)
    if st.button("1. Estimate cost (runs the same selection in fake mode, free)"):
        name = f"estimate_{stamp}"
        st.session_state.estimates[key] = {"queue": name}
        launch_queue([{**c, "llm": {**c["llm"], "mode": "fake"}, "run_name": "estimate_" + c["run_name"]}
                      for c in configs], name)
        st.session_state.active_queue = name
        st.rerun()
    if not estimate:
        return
    if not queue_done(estimate["queue"]):
        st.info("Estimating... (see the progress panel below)")
        return
    usd = queue_cost(estimate["queue"])
    st.warning(f"Estimated cost: about **${usd:.2f}**. This counts input tokens from a fake run; real "
               "answers and writer outputs are longer, so treat it as a lower bound.")
    approved = st.checkbox(f"I approve spending about ${usd:.2f} (and possibly more) on this run")
    if st.button("2. Run with real Claude Haiku 5.5", type="primary", disabled=not approved):
        st.session_state.active_queue = f"real_{stamp}"
        launch_queue(configs, st.session_state.active_queue)


@st.fragment(run_every=2)
def progress_panel() -> None:
    name = st.session_state.get("active_queue")
    if not name:
        return
    st.subheader(f"Progress: {name}")
    events = queue_events(name)
    for e in events:
        if e["status"] in ("started", "finished", "failed"):
            icon = {"started": "▶", "finished": "✓", "failed": "✗"}[e["status"]]
            st.write(f"{icon} {e.get('run_name') or Path(e['config']).stem}" + (f": {e['error']}" if "error" in e else ""))
    running = [e for e in events if e["status"] == "started"]
    if running:
        logs = sorted((results_dir() / "runs").glob(f"{running[-1]['run_name']}_*/run.log"))
        if logs:
            st.code(tail(logs[-1]) or "(starting)", language="text")
    if any(e["status"] == "done" for e in events):
        st.success("Queue finished. See the Results tab.")
    elif (queues_dir() / f"{name}.out").exists():
        errors = tail(queues_dir() / f"{name}.out", 15)
        if "Traceback" in errors:
            st.code(errors, language="text")


# ---------------------------------------------------------------------------- train tab

def train_tab() -> None:
    st.subheader("Train the GNN")
    st.caption("GOAt's GCN_NC (3 GCN layers + 2 linear). Never trained on MemoryAgentBench or MQuAKE data.")
    c1, c2, c3 = st.columns(3)
    source = c1.selectbox("Training data", ["synthetic", "subgraphrag", "both"],
                          help="synthetic: invented worlds with revisions; subgraphrag: WebQSP + CWQ (downloads)")
    embedding = c1.selectbox("Embedding model", EMBEDDINGS, key="train_emb",
                             help="must match the embedding model of the runs that use this checkpoint")
    epochs = c2.number_input("Epochs", 1, 500, 30)
    worlds = c2.number_input("Synthetic worlds", 2, 2000, 40)
    qpw = c2.number_input("Questions per world", 5, 500, 30)
    limit = c3.number_input("SubgraphRAG questions", 10, 50000, 1000)
    hidden = c3.number_input("Hidden size", 8, 512, 64)
    name = c3.text_input("Checkpoint name", f"gnn_{source}_{time.strftime('%m%d-%H%M')}")
    if st.button("Train", type="primary"):
        out = results_dir() / "checkpoints" / name
        out.mkdir(parents=True, exist_ok=True)
        cmd = [PYTHON, "-m", "my_method.gnn.train", "--source", source, "--out", str(out), "--embedding-model",
               embedding, "--epochs", str(epochs), "--synthetic-worlds", str(worlds), "--questions-per-world",
               str(qpw), "--subgraphrag-limit", str(limit), "--hidden", str(hidden)]
        subprocess.Popen(cmd, cwd=REPO, stdout=open(out / "train.log", "w"), stderr=subprocess.STDOUT,
                         env={**os.environ, "PYTHONPATH": str(REPO)}, start_new_session=True)
        st.session_state.training = str(out)
    root = results_dir() / "checkpoints"
    runs = sorted(root.glob("*/metrics.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True) if root.exists() else []
    if runs:
        default = next((i for i, p in enumerate(runs) if str(p.parent) == st.session_state.get("training")), 0)
        st.session_state.watch = str(st.selectbox("Watch checkpoint", runs, index=default,
                                                  format_func=lambda p: p.parent.name).parent)
        training_chart()


@st.fragment(run_every=2)
def training_chart() -> None:
    folder = Path(st.session_state.watch)
    rows = [json.loads(line) for line in open(folder / "metrics.jsonl")] if (folder / "metrics.jsonl").exists() else []
    if rows:
        df = pd.DataFrame(rows).set_index("epoch")
        c1, c2 = st.columns(2)
        c1.markdown("**Loss**")
        c1.line_chart(df[["train_loss", "val_loss"]])
        recall = [c for c in df.columns if c.startswith("val_answer_recall")]
        c2.markdown("**Validation: answer node in top 10**")
        c2.line_chart(df[recall])
    st.code(tail(folder / "train.log", 12) or "(waiting for output)", language="text")


# ---------------------------------------------------------------------------- results / runs tabs

def results_tab() -> None:
    c1, c2 = st.columns(2)
    length = c1.selectbox("Length", LENGTHS, index=LENGTHS.index("6k"), key="res_len")
    mode = c2.selectbox("LLM mode", ["real", "fake"], key="res_mode")
    out = build_table(length, mode)
    st.markdown(out.with_suffix(".md").read_text())
    st.caption(f"Saved as {out.with_suffix('.csv').relative_to(REPO)} and .md")


def runs_tab() -> None:
    summaries = sorted((results_dir() / "runs").glob("*/summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not summaries:
        st.info("No runs yet.")
        return
    rows = []
    for path in summaries:
        s = json.loads(path.read_text())
        rows.append({"run": path.parent.name, "method": s["display"], "variant": s.get("variant", ""),
                     "length": s["length"], "llm": s["llm_mode"],
                     "FC-SH": round(s["accuracy"]["sh"]["mean"], 1), "FC-MH": round(s["accuracy"]["mh"]["mean"], 1),
                     "cost $": round(s["api_cost_usd"]["total"], 4)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    run = st.selectbox("Inspect a run", [r["run"] for r in rows])
    folder = results_dir() / "runs" / run
    st.code((folder / "config.yaml").read_text(), language="yaml")
    cfg = yaml.safe_load((folder / "config.yaml").read_text())
    if cfg["llm"]["mode"] == "fake" and st.button("Re-run this exact config (fake)"):
        st.session_state.active_queue = f"rerun_{time.strftime('%Y%m%d-%H%M%S')}"
        launch_queue([cfg], st.session_state.active_queue)
    elif cfg["llm"]["mode"] == "real":
        st.caption("Real runs are re-run from the Run tab, so they go through the cost estimate and approval.")
    scored = folder / "repeat_0" / "scored.jsonl"
    if scored.exists():
        st.markdown("**Answers (repeat 0)**")
        df = pd.DataFrame(json.loads(line) for line in open(scored))
        cols = [c for c in ["split", "answers", "prediction", "substring_exact_match", "answer_in_retrieved",
                            "input_tokens", "cost_usd"] if c in df.columns]
        st.dataframe(df[cols], hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------- page

for name, value in {"variants": [], "estimates": {}}.items():
    st.session_state.setdefault(name, value)

mode_html = ('<span class="mode-real">REAL API KEY PRESENT</span>' if os.environ.get("ANTHROPIC_API_KEY")
             else '<span class="mode-fake">offline: no API key in environment</span>')
st.markdown(f'<div class="sgar-topbar"><div class="brand">SGAR test bench</div><div>{mode_html}</div></div>',
            unsafe_allow_html=True)
tab_run, tab_train, tab_results, tab_runs = st.tabs(["Run", "Train GNN", "Results", "Runs"])
with tab_run:
    run_tab()
    progress_panel()
with tab_train:
    train_tab()
with tab_results:
    results_tab()
with tab_runs:
    runs_tab()
