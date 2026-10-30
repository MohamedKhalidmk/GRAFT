#!/usr/bin/env bash
# Environment for upstream Letta: the last release of the Letta (MemGPT) API server, 0.16.8
# (2026-05-14). Later PyPI `letta` versions (0.32+) are Letta Code, a different product, and the
# server source now lives only on the archive branch. letta-client is pinned to the last release
# before that server (1.10.3); dependencies are resolved as of the server release date. The server
# needs Postgres + pgvector (SQLite support was removed in 0.12): `pgserver` provides Postgres 16 and
# pgvector binaries as a wheel; asyncpg, pg8000 and pgvector are its Postgres drivers. The wheel has no
# schema migrations, so the alembic/ directory is taken from the same release's sdist. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/../.."
UV=.venv/bin/uv
ENV=envs/letta-upstream
[ -x "$ENV/bin/python" ] || "$UV" venv --python "${PYTHON312:-python3.12}" "$ENV"
"$UV" pip install --python "$ENV/bin/python" --exclude-newer 2026-05-15 "letta[server]==0.16.8" "letta-client==1.10.3" asyncpg pg8000 pgvector pgserver==0.1.4

SDIST_URL=https://files.pythonhosted.org/packages/6a/94/b51b0746dd862b86538f10085b57c216ab32e3d40532e45b63afe0925c4c/letta-0.16.8.tar.gz
SDIST_SHA256=363e26989e552c859ce2e7961d484acee6fccfc1e7b16e8f644b1ae1ccd754a3
MIGRATIONS=$ENV/letta-migrations
if [ ! -f "$MIGRATIONS/alembic.ini" ]; then
  tmp=$(mktemp -d)
  curl -sSfL -o "$tmp/letta.tar.gz" "$SDIST_URL"
  echo "$SDIST_SHA256  $tmp/letta.tar.gz" | shasum -a 256 -c -
  tar xzf "$tmp/letta.tar.gz" -C "$tmp" letta-0.16.8/alembic letta-0.16.8/alembic.ini
  mkdir -p "$MIGRATIONS"
  mv "$tmp/letta-0.16.8/alembic" "$tmp/letta-0.16.8/alembic.ini" "$MIGRATIONS/"
  rm -rf "$tmp"
fi
