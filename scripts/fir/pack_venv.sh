#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=2:00:00
#SBATCH --job-name=graft-pack-venv
#SBATCH --output=%x-%j.out
# Pack the repo's .venv into one archive on scratch, which common.sh unpacks to each job's local disk.
# Rerun after any change to the venv: sbatch scripts/fir/pack_venv.sh
set -euo pipefail
GRAFT_LOCAL=0 source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
t0=$(date +%s)
tar cf "$SCRATCH_ROOT/venv.tar.part" -C "$REPO" .venv
mv "$SCRATCH_ROOT/venv.tar.part" "$SCRATCH_ROOT/venv.tar"
ls -la "$SCRATCH_ROOT/venv.tar"; echo "packed in $(( $(date +%s) - t0 )) s"
