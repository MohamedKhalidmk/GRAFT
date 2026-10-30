#!/usr/bin/env bash
# Run once on a Fir LOGIN node (it has internet): environments, data and model downloads.
# Compute nodes may have no internet, so everything a job needs is fetched here first.
# Core environment only; add the third-party baselines with scripts/setup_envs.sh <names>.
#   bash scripts/fir/setup_login_node.sh "Qwen/Qwen3-Embedding-0.6B"
set -euo pipefail
source "$(dirname "$0")/common.sh"
chmod 700 "$REPO"
[ -x .venv/bin/python ] || virtualenv --no-download --system-site-packages .venv  # sees the arrow module
# torch and PyG from the cluster's own wheels (built for its CPUs and GPUs), the rest from PyPI
.venv/bin/pip install -q --no-index --upgrade pip
.venv/bin/pip install -q --no-index torch torch_geometric
.venv/bin/pip install -q anthropic datasets editdistance langchain-community langchain-core matplotlib \
    networkx nltk pandas pytest PyYAML rank-bm25 rouge_score scipy sentence-transformers tiktoken
.venv/bin/python -m data.download
.venv/bin/python -c "import nltk, tiktoken; nltk.download('punkt'); nltk.download('punkt_tab'); tiktoken.encoding_for_model('gpt-4o-mini')"
EMB="${1:-Qwen/Qwen3-Embedding-0.6B}"
.venv/bin/python -c "from sentence_transformers import SentenceTransformer as S; S('$EMB', trust_remote_code=True)"
echo "Ready. Check API access from a compute node before real runs: sbatch scripts/fir/check_internet.sbatch"
