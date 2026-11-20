#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=01:30:00
#SBATCH --job-name=graft-stopword-links
#SBATCH --output=%x-%j.out
# Free before/after count of single-stopword links. Usage (repo root): sbatch scripts/fir/stopword_links.sbatch GRAPH PRED [QUERY_LINKING]
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
.venv/bin/python scripts/fir/stopword_links.py "$@"
