#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --job-name=graft-ppr-check
#SBATCH --output=%x-%j.out
# Free PageRank stop-rule check on the full T-REx graph. Usage (repo root): sbatch scripts/fir/ppr_check.sbatch GRAPH PRED
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
.venv/bin/python scripts/fir/ppr_check.py "$@"
