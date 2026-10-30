#!/usr/bin/env bash
# Environment for upstream Mem0: mem0ai from PyPI (https://github.com/mem0ai/mem0), pinned to the
# latest release when this baseline was added. Mem0 2.x searches with semantic + BM25 + entity
# boosts; without the optional parts it silently falls back to semantic-only search. So we add the
# [nlp] extra (spaCy + en_core_web_sm: lemmatization, entity linking) and fastembed (the Qdrant/bm25
# sparse encoder; the [extras] extra would also pull torch/sentence-transformers, which Mem0 does not
# use here). Models Mem0 would otherwise download at run time are fetched here: en_core_web_sm into
# the env, Qdrant/bm25 (~100KB) into $ENV/fastembed_cache (the agent sets FASTEMBED_CACHE_PATH).
# Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/mem0-upstream
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" "mem0ai[nlp]==2.2.1" \
  "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl" \
  "fastembed==0.9.1"
FASTEMBED_CACHE_PATH="$ENV/fastembed_cache" "$ENV/bin/python" -c 'from fastembed import SparseTextEmbedding; SparseTextEmbedding(model_name="Qdrant/bm25")'
"$ENV/bin/python" -c 'import importlib.metadata as m, spacy; spacy.load("en_core_web_sm"); print("mem0ai", m.version("mem0ai"), "spacy", spacy.__version__)'
