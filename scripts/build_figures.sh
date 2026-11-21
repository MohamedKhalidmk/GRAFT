#!/usr/bin/env bash
# Rebuild every test's table.csv, table.md and figure.png from its runs, then assets/results.png from those tables.
# Local and light (matplotlib only, no API calls). Uses $PYTHON, else .venv/bin/python, else python3.
#   bash scripts/build_figures.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-}"
[ -n "$PY" ] || { [ -x .venv/bin/python ] && PY=.venv/bin/python || PY=python3; }
for t in experiments/test-0*/make_table.py; do
  echo "== $t"
  "$PY" "$t" > /dev/null
done
"$PY" docs/design/theme/results_chart.py --check
"$PY" docs/design/theme/results_chart.py
