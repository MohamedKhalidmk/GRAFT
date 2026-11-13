#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=06:00:00
#SBATCH --job-name=sgar-goat-full
#SBATCH --output=%x-%j.out
# Time GOAt on the whole 262K graph for one question, on CPU (as the method runs it) and on the GPU.
# Submit from the repo root: cd ~/projects/def-sylu/khaledmk/SGAR && sbatch scripts/fir/time_goat_full.sbatch
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
/usr/bin/time -v .venv/bin/python scripts/fir/time_goat_full.py --device cpu 2>&1 | grep -v '^\s*\(Page\|File\|Socket\|Signals\|Swaps\|Average\|Voluntary\|Involuntary\|Exit\|Minor\|Major\|Percent\)'
.venv/bin/python scripts/fir/time_goat_full.py --device cuda
