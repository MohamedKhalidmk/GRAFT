#!/usr/bin/env bash
# Create every environment: the core .venv, then one per third-party baseline (scripts/setup/*.sh).
# Idempotent. Set PYTHON312 if python3.12 is not on PATH.
#   bash scripts/setup_envs.sh            # all
#   bash scripts/setup_envs.sh mem0-bundled letta-bundled
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON312:-python3.12}"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/pip install -q uv
.venv/bin/uv pip install --python .venv/bin/python -r requirements.txt
git submodule update --init
names=("$@")
[ ${#names[@]} -gt 0 ] || names=($(ls scripts/setup | sed 's/\.sh$//'))
for name in "${names[@]}"; do
  echo "== $name"
  bash "scripts/setup/$name.sh" || echo "!! $name failed (see output above)"
done
