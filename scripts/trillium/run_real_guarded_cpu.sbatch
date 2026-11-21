#!/bin/bash
#SBATCH --account=def-sylu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=192
#SBATCH --time=08:00:00
#SBATCH --job-name=graft-real-cpu
#SBATCH --output=%x-%j.out
# Trillium twin of scripts/fir/run_real_guarded_cpu.sbatch. Trillium gives whole nodes (192 cores, no --mem);
# submit from $SCRATCH/sgar/SGAR (home and project are read-only on compute nodes). CPU nodes (GRAFT retrieval, GNN and embeddings never use a GPU). PAID runs with a cost guard: runs the given configs one after another (eval.queue) and every
# minute adds up cost_usd from this job's usage logs; past COST_CAP_USD (default 15) it stops.
# The key comes from the submitting shell's environment; never put it on disk. Trillium's sbatch puts --export=NONE on
# the command line (an #SBATCH line cannot override it), so submit with sbatch --export=ALL or the key is not passed on.
# NOTE: Trillium compute nodes have no internet, so real (paid) configs stop at the reachability check below; only
# fake-mode (free) configs run here. Kept as the twin in case outside access is added.
#   cd $SCRATCH/sgar/SGAR && sbatch --export=ALL scripts/trillium/run_real_guarded_cpu.sbatch configs/runs/exp/a_real_mh_262k.yaml ...
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/trillium/common.sh"
export HF_HUB_OFFLINE=1
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs sbatch, and submit with sbatch --export=ALL}"
# Trillium compute nodes had no internet on 2026-11-21 (api.anthropic.com timed out), so a real run cannot reach the
# API from here. Check first (unauthenticated, nothing billed) and stop at once instead of failing every question.
if [[ -n "$(grep -L '^  mode: fake' "$@" || true)" ]]; then  # some config is not fake mode
  env -u https_proxy -u HTTPS_PROXY curl -s -o /dev/null --max-time 20 https://api.anthropic.com/v1/models \
    || { echo "api.anthropic.com unreachable from this compute node: paid runs cannot run on Trillium"; exit 4; }
fi
CAP="${COST_CAP_USD:-15}"
START=$(date +%s)
setsid .venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@" &
QPID=$!
# only this job's runs: the run_name of every config it was given (other jobs write to the same results folder)
RUN_NAMES=$(for c in "$@"; do sed -n 's/^run_name: *//p' "$c"; done | tr '\n' ' ')
spent() {
  .venv/bin/python - "$START" $RUN_NAMES <<'EOF'
import glob, json, os, sys
start, total = float(sys.argv[1]), 0.0
paths = [p for name in sys.argv[2:] for p in glob.glob(os.environ["RESULTS_DIR"] + f"/runs/{name}_2*/repeat_*/usage.jsonl")]
for path in paths:
    if os.path.getmtime(path) < start:
        continue  # an earlier job's run
    for line in open(path):
        try:
            total += json.loads(line)["cost_usd"]
        except (ValueError, KeyError):
            pass
print(f"{total:.4f}")
EOF
}
while kill -0 "$QPID" 2>/dev/null; do
  sleep 60
  SPENT=$(spent)
  echo "[cost guard] $(date +%H:%M) spent \$$SPENT of \$$CAP"
  if awk -v s="$SPENT" -v c="$CAP" 'BEGIN{exit !(s > c)}'; then
    echo "[cost guard] over the cap: stopping every run"
    kill -TERM -- -"$QPID" 2>/dev/null || true
    exit 3
  fi
done
wait "$QPID"
echo "[cost guard] finished, total \$$(spent)"
