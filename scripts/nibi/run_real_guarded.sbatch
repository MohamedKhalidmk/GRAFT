#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --job-name=graft-real
#SBATCH --output=%x-%j.out
# Nibi twin of scripts/fir/run_real_guarded.sbatch (one H100). PAID runs with a cost guard: runs the given configs one after another (eval.queue) and every
# minute adds up cost_usd from this job's usage logs; past COST_CAP_USD (default 15) it stops.
# The key comes from the submitting shell's environment (sbatch passes it on); never put it on disk.
#   cd ~/projects/def-sylu/khaledmk/SGAR && sbatch scripts/nibi/run_real_guarded.sbatch configs/runs/exp/a_real_mh_262k.yaml ...
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/nibi/common.sh"
export HF_HUB_OFFLINE=1
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs sbatch}"
CAP="${COST_CAP_USD:-15}"
START=$(date +%s)
# fixed Haiku check (2026-11-21): a one-repeat replay of the 2026-11-13 run's facts goes first in every batch that calls
# Haiku, so a change on the API side shows up as a moved score on identical inputs (CANARY=0 skips it)
CONFIGS=("$@")
if [[ "${CANARY:-1}" == 1 ]] && grep -qs "model: claude-haiku" "${CONFIGS[@]}"; then
  CONFIGS=(configs/runs/exp/canary/haiku_replay38.yaml "${CONFIGS[@]}")
fi
setsid .venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "${CONFIGS[@]}" &
QPID=$!
# only this job's runs: the run_name of every config it was given (other jobs write to the same results folder)
RUN_NAMES=$(for c in "${CONFIGS[@]}"; do sed -n 's/^run_name: *//p' "$c"; done | tr '\n' ' ')
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
