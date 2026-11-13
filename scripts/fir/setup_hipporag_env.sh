#!/usr/bin/env bash
# Fir LOGIN node, once: the environment for the benchmark's bundled HippoRAG (envs/hipporag-bundled).
# Same package pins as scripts/setup/hipporag-bundled.sh (the Mac version), with Fir's rules:
# torch from the cluster's own wheels (--no-index), pyarrow from the arrow module (loaded by
# common.sh; the env sees it through --system-site-packages), the rest from PyPI. In gateway mode
# HippoRAG never runs a model itself (embeddings and LLM calls go through the gateway), so the
# torch version does not change results. vllm is not installed (the agent stubs it).
#   bash scripts/fir/setup_hipporag_env.sh
set -euo pipefail
source "$(dirname "$0")/common.sh"
ENV=envs/hipporag-bundled
[ -x "$ENV/bin/python" ] || virtualenv --no-download --system-site-packages "$ENV"
"$ENV/bin/pip" install -q --no-index --upgrade pip
"$ENV/bin/pip" install -q --no-index torch
"$ENV/bin/pip" install -q "transformers==4.45.2" "openai==1.58.1" "networkx==3.4.2" "python-igraph==0.11.8" \
  "tiktoken==0.7.0" "pydantic==2.10.4" "tenacity==8.5.0" einops tqdm pandas filelock accelerate
"$ENV/bin/pip" install -q --no-deps "gritlm==1.0.2"

SRC="$REPO/$ENV/bundled_src"
mkdir -p "$SRC"
ln -sfn "$REPO/baselines/memoryagentbench/methods/hipporag" "$SRC/hipporag"
SITE="$("$ENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "$SRC" > "$SITE/hipporag_bundled_src.pth"
"$ENV/bin/python" -c 'import importlib.util as u, os; print("hipporag (bundled)", os.path.realpath(u.find_spec("hipporag").submodule_search_locations[0]))'
"$ENV/bin/python" -c 'import torch, transformers, openai, igraph, pyarrow; print("torch", torch.__version__, "| transformers", transformers.__version__, "| openai", openai.__version__, "| pyarrow", pyarrow.__version__)'
