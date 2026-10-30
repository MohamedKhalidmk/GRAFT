#!/usr/bin/env bash
# Environment for Knowl (github.com/dat999zx/knowl), driven through the benchmark's Node bridge
# (benchmarks/memoryagentbench/mab-bridge.ts, imported by methods/knowl.py). Everything lives in
# the env: a Node 22 runtime from the nodejs-wheel package (Knowl needs node >= 22), the Knowl
# source at v5.6.0 (the release of the day the method was contributed) with its npm dependencies,
# the built bridge, and the OpenAI client the reader call uses (pointed at the Claude gateway).
# Knowl's embedding weights (granite-small-en-r2, ~52 MB) are fetched into $ENV/models on the
# first run. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/knowl
KNOWL_REF=v5.6.0
SRC="$ENV/src/knowl"
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" "nodejs-wheel==22.20.0" "openai==3.41.0"
export PATH="$PWD/$ENV/bin:$PATH" npm_config_cache="$PWD/$ENV/.npm-cache"
[ -d "$SRC/.git" ] || git -c advice.detachedHead=false clone --depth 1 --branch "$KNOWL_REF" https://github.com/dat999zx/knowl.git "$SRC"
cd "$SRC"
# Install scripts are skipped: the bridge needs none of them (onnxruntime-node and libsql ship
# prebuilt binaries; esbuild's binary comes from its platform package; tree-sitter is not on the
# bridge's import path).
[ -d node_modules ] || { npm ci --ignore-scripts --no-audit --no-fund; rm -rf "$npm_config_cache"; }
[ -f .benchmark-dist/mab-bridge.js ] || ./node_modules/.bin/tsup benchmarks/memoryagentbench/mab-bridge.ts --format esm --outDir .benchmark-dist --no-dts
mkdir -p ../../models
echo "knowl $(git describe --tags), node $(node --version)"
