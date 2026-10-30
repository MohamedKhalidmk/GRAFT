#!/usr/bin/env bash
# Environment for upstream HippoRAG: hipporag from PyPI (https://github.com/OSU-NLP-Group/HippoRAG),
# pinned to 2.0.0a4, the latest release when this baseline was added. Its own pins are installed
# as declared (resolved as of its release day, --exclude-newer), with two exceptions: openai==1.91.1 is not on PyPI (so `pip install
# hipporag==2.0.0a4` fails as is), we use 1.91.0; and vllm==0.6.6.post1 has Linux/CUDA wheels only
# and is used only by HippoRAG's offline-OpenIE mode (the agent stubs the import when it is
# missing). gritlm is installed without its training/eval dependencies (wandb, mteb, datasets):
# HippoRAG only imports its GritLM class. pyarrow is needed by HippoRAG's parquet embedding store
# but not declared. Set HIPPORAG_WITH_VLLM=1 on a Linux GPU host to install vllm too. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/hipporag-upstream
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" --no-deps "hipporag==2.0.0a4" "gritlm==1.0.2"
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2025-06-25 \
  "torch==2.5.1" "transformers==4.45.2" "openai==1.91.0" "litellm==1.73.1" "networkx==3.4.2" \
  "python-igraph==0.11.8" "tiktoken==0.7.0" "pydantic==2.10.4" "tenacity==8.5.0" einops tqdm boto3 \
  pandas pyarrow filelock accelerate
if [ "${HIPPORAG_WITH_VLLM:-0}" = 1 ]; then
  "$UV" pip install --python "$ENV/bin/python" "vllm==0.6.6.post1"
fi
"$ENV/bin/python" -c 'import importlib.util as u, os; print("hipporag (upstream)", os.path.realpath(u.find_spec("hipporag").submodule_search_locations[0]))'
