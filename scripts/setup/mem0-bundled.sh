#!/usr/bin/env bash
# Environment for the benchmark's bundled Mem0 (baselines/memoryagentbench/mem0).
# The bundled copy is byte-identical to mem0ai 0.1.88 (all 90 .py files match the PyPI wheel).
# We install only mem0ai 0.1.88's declared dependencies, resolved as of its release day
# (--exclude-newer), and never the mem0ai package itself. The bundled source is exposed through a
# .pth entry for a directory holding just a `mem0` symlink plus a minimal mem0ai-0.1.88.dist-info
# (mem0/__init__.py reads importlib.metadata.version("mem0ai")). Adding the benchmark root to
# sys.path instead would also expose its top-level `utils`, `letta`, `cognee`. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$(pwd)"
UV=.venv/bin/uv
ENV=envs/mem0-bundled
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2025-04-10 \
  "openai>=1.33.0,<2.0.0" "posthog>=3.5.0,<4.0.0" "psycopg2-binary>=2.9.10,<3.0.0" \
  "pydantic>=2.7.3,<3.0.0" "pytz>=2024.1,<2025.0" "qdrant-client>=1.9.1,<2.0.0" "sqlalchemy>=2.0.31,<3.0.0"

SRC="$REPO/$ENV/bundled_src"
mkdir -p "$SRC/mem0ai-0.1.88.dist-info"
ln -sfn "$REPO/baselines/memoryagentbench/mem0" "$SRC/mem0"
printf 'Metadata-Version: 2.1\nName: mem0ai\nVersion: 0.1.88\nSummary: Bundled copy from baselines/memoryagentbench/mem0\n' \
  > "$SRC/mem0ai-0.1.88.dist-info/METADATA"
SITE="$("$ENV/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "$SRC" > "$SITE/mem0_bundled_src.pth"
"$ENV/bin/python" -c 'import mem0, os; assert mem0.__version__ == "0.1.88"; print("mem0", mem0.__version__, os.path.realpath(mem0.__file__))'
