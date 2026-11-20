#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=160G
#SBATCH --time=02:00:00
#SBATCH --job-name=graft-clean-base
#SBATCH --output=%x-%j.out
# Free: drop junk-named base entities. Usage (repo root): sbatch scripts/fir/clean_base.sbatch BASE SHARED SUFFIX
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
.venv/bin/python scripts/fir/clean_base.py "$@"
