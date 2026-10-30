#!/usr/bin/env bash
# Environment for the benchmark's bundled HippoRAG (baselines/memoryagentbench/methods/hipporag),
# a modified copy of hipporag 2.0.0a3 (its prompt templates are identical to the 2.0.0a3 wheel).
# We install 2.0.0a3's declared dependencies, resolved as of its release day (--exclude-newer),
# except vllm (Linux/CUDA only; only HippoRAG's offline-OpenIE mode uses it, and the agent stubs
# the import) and never the hipporag package itself; plus pyarrow, which HippoRAG's parquet
# embedding store needs but does not declare. gritlm is installed without its training/eval
# dependencies (wandb, mteb, datasets): HippoRAG only imports its GritLM class.
# The bundled source is exposed as the top-level package `hipporag` through a .pth entry for a
# directory holding just a `hipporag` symlink: its PromptTemplateManager imports templates as
# `hipporag.prompts.templates.*`, and adding the benchmark root to sys.path instead would expose
# its top-level `utils`, `mem0`, `letta`, `cognee`. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$(pwd)"
UV=.venv/bin/uv
ENV=envs/hipporag-bundled
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2025-04-13 \
  "torch==2.5.1" "transformers==4.45.2" "openai==1.58.1" "networkx==3.4.2" "python-igraph==0.11.8" \
  "tiktoken==0.7.0" "pydantic==2.10.4" "tenacity==8.5.0" einops tqdm pandas pyarrow filelock accelerate
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2025-04-13 --no-deps "gritlm==1.0.2"

SRC="$REPO/$ENV/bundled_src"
mkdir -p "$SRC"
ln -sfn "$REPO/baselines/memoryagentbench/methods/hipporag" "$SRC/hipporag"
SITE="$("$ENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "$SRC" > "$SITE/hipporag_bundled_src.pth"
"$ENV/bin/python" -c 'import importlib.util as u, os; print("hipporag (bundled)", os.path.realpath(u.find_spec("hipporag").submodule_search_locations[0]))'
