#!/bin/bash
#SBATCH --account=def-sylu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=192
#SBATCH --time=02:00:00
#SBATCH --job-name=graft-cpu
#SBATCH --output=%x-%j.out
# Trillium twin of scripts/fir/run_cpu_queue.sbatch (free runs; whole node, no --mem; submit from $SCRATCH/sgar/SGAR).
# Run a queue of fake-mode configs on CPUs. GOAt is per-question CPU work, so set
# method_config.retrieval_workers to about --cpus-per-task; a GPU would not speed it up.
# Usage: sbatch scripts/trillium/run_cpu_queue.sbatch configs/runs/a.yaml ...
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/trillium/common.sh"  # submit from $SCRATCH/sgar/SGAR
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 OMP_NUM_THREADS=1
.venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@"
