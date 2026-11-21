#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --job-name=trex-guide
#SBATCH --output=%x-%j.out
# Test 06 step 0 (free, no LLM): T-REx structure guide + coverage of the question parses and document relations.
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
B=$(ls -d $RESULTS_DIR/runs/exp_wm_empty_b_qlayer_2* | tail -1)
.venv/bin/python scripts/trex_guide.py --base results/checkpoints/base_graphs/trex_full_base.json \
  --docs results/checkpoints/shared_graphs/real_mh_262k_empty_start.json \
  --parses $B/repeat_0/predictions.jsonl --out $RESULTS_DIR/checkpoints/trex_guide.json
