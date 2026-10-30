#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:nvidia_h100_80gb_hbm3_1g.10gb:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --job-name=sgar-runs
#SBATCH --output=%x-%j.out
# Run a queue of run configs (the GPU serves the shared embedding model; HippoRAG with NV-Embed-v2
# needs the full H100: use --gres=gpu:h100:1 for that). Real-mode configs need ANTHROPIC_API_KEY
# exported in the submitting shell (sbatch passes the environment; the key is never written to disk).
# Usage: sbatch scripts/fir/run_queue.sbatch configs/runs/a.yaml configs/runs/b.yaml ...
set -euo pipefail
source "$HOME/SGAR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
.venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@"
