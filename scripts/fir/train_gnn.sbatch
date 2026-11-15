#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:nvidia_h100_80gb_hbm3_1g.10gb:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --job-name=graft-gnn
#SBATCH --output=%x-%j.out
# Train GRAFT's GNN. No API calls. A 1g.10gb H100 slice is plenty for a 3-layer GCN plus a small
# embedding model. Usage: sbatch scripts/fir/train_gnn.sbatch <source> <checkpoint name> [embedding model]
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"  # submit from the repo root
export HF_HUB_OFFLINE=1
.venv/bin/python -m my_method.gnn.train --source "${1:-synthetic}" --out "$RESULTS_DIR/checkpoints/${2:-gnn_default}" \
  --embedding-model "${3:-Qwen/Qwen3-Embedding-0.6B}" --synthetic-worlds 400 --questions-per-world 30 --epochs 30
