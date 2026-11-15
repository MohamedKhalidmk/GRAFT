#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --job-name=graft-real
#SBATCH --output=%x-%j.out
# PAID runs with a cost guard: runs the given configs one after another (eval.queue) and every
# minute adds up cost_usd from this job's usage logs; past COST_CAP_USD (default 15) it stops.
# The key comes from the submitting shell's environment (sbatch passes it on); never put it on disk.
#   cd ~/projects/def-sylu/khaledmk/SGAR && sbatch scripts/fir/run_real_guarded.sbatch configs/runs/exp/a_real_mh_262k.yaml ...
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY in the shell that runs sbatch}"
CAP="${COST_CAP_USD:-15}"
START=$(date +%s)
setsid .venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@" &
QPID=$!
spent() {
  .venv/bin/python - "$START" <<'EOF'
import glob, json, os, sys
start, total = float(sys.argv[1]), 0.0
for path in glob.glob(os.environ["RESULTS_DIR"] + "/runs/exp_*real*/repeat_*/usage.jsonl"):
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
