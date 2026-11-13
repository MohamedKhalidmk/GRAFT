#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --job-name=sgar-cpu
#SBATCH --output=%x-%j.out
# Run a queue of fake-mode configs on CPUs. GOAt is per-question CPU work, so set
# method_config.retrieval_workers to about --cpus-per-task; a GPU would not speed it up.
# Usage: sbatch scripts/fir/run_cpu_queue.sbatch configs/runs/a.yaml ...
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"  # submit from the repo root
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 OMP_NUM_THREADS=1
.venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@"
