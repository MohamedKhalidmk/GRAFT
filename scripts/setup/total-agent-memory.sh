#!/usr/bin/env bash
# Environment for total-agent-memory (github.com/vbcherepanov/total-agent-memory): the PyPI
# release the benchmark's methods/total_agent_memory.py pins, plus the OpenAI client the reader
# call uses (pointed at the Claude gateway). TAM's FastEmbed weights (~330 MB) are fetched into
# $ENV/models on the first run. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/total-agent-memory
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" "total-agent-memory==14.5.1" "openai==3.41.0"
mkdir -p "$ENV/models"
"$ENV/bin/python" -c 'import importlib.metadata as m; print("total-agent-memory", m.version("total-agent-memory"))'
