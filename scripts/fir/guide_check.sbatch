#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --job-name=guide-check
#SBATCH --output=%x-%j.out
# Test 06 arm B dry check (free, no LLM): guide linking + planning on the real graph with arm B's logged parses.
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
B=$(ls -d $RESULTS_DIR/runs/exp_wm_empty_b_qlayer_2* | tail -1)
.venv/bin/python scripts/guide_check.py --guide results/checkpoints/trex_guide.json \
  --graph results/checkpoints/shared_graphs/real_mh_262k_empty_start.json --run $B --out $RESULTS_DIR/guide_check.json
