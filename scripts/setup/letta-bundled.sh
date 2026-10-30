#!/usr/bin/env bash
# Environment for the benchmark's bundled Letta 0.7.0 (baselines/memoryagentbench/letta).
# The bundled package is imported from the submodule, so we install letta==0.7.0 from PyPI only
# for its dependency set (resolved as of its release date) and then remove the PyPI package
# itself. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/letta-bundled
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2025-04-22 "letta==0.7.0"
"$UV" pip uninstall --python "$ENV/bin/python" letta
