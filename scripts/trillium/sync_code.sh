#!/bin/bash
# Run on the Mac from the repo root: replace the Trillium code copy ($SCRATCH/sgar/SGAR) with the committed HEAD
# (git archive) plus the two submodules (baselines/memoryagentbench, my_method/gnn/GOAt), which git archive leaves
# out. Uncommitted edits are not copied. Keeps results/ (results/checkpoints links to scratch) and job .out files.
# Uses the CPU login node's ssh socket; TRILLIUM_HOST=trillium-gpu.alliancecan.ca uses the GPU login node's (trig-login01).
#   bash scripts/trillium/sync_code.sh
set -euo pipefail
DIR=/scratch/khaledmk/sgar/SGAR
s() { ssh -o BatchMode=yes -o ControlPath="$HOME/.ssh/cm-%r@%h:%p" khaledmk@${TRILLIUM_HOST:-trillium.alliancecan.ca} "$@"; }
s "mkdir -p $DIR && cd $DIR && find . -mindepth 1 -maxdepth 1 ! -name results ! -name '*.out' -exec rm -rf {} +"
git archive HEAD | s "tar xf - -C $DIR"
COPYFILE_DISABLE=1 tar cf - --no-xattrs --exclude=.git --exclude=__pycache__ --exclude=.DS_Store \
  baselines/memoryagentbench my_method/gnn/GOAt | s "tar xf - -C $DIR"
s "cd $DIR && mkdir -p results && ln -sfn /scratch/khaledmk/sgar/results/checkpoints results/checkpoints"
echo "Trillium code at $(git rev-parse --short HEAD)"
