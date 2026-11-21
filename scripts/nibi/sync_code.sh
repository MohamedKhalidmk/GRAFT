#!/bin/bash
# Run on the Mac from the repo root: replace the Nibi code copy with the committed HEAD (git archive) plus the two
# submodules (baselines/memoryagentbench, my_method/gnn/GOAt), which git archive leaves out. Uncommitted edits are
# not copied. Keeps results/ (results/checkpoints links to scratch) and job .out files. Needs a live ssh socket.
#   bash scripts/nibi/sync_code.sh
set -euo pipefail
DIR=/home/khaledmk/projects/def-sylu/khaledmk/SGAR
s() { ssh -o BatchMode=yes -o ControlPath="$HOME/.ssh/cm-%r@%h:%p" khaledmk@nibi.alliancecan.ca "$@"; }
s "mkdir -p $DIR && cd $DIR && find . -mindepth 1 -maxdepth 1 ! -name results ! -name '*.out' -exec rm -rf {} +"
git archive HEAD | s "tar xf - -C $DIR"
COPYFILE_DISABLE=1 tar cf - --no-xattrs --exclude=.git --exclude=__pycache__ --exclude=.DS_Store \
  baselines/memoryagentbench my_method/gnn/GOAt | s "tar xf - -C $DIR"
s "cd $DIR && mkdir -p results && ln -sfn \$HOME/scratch/sgar/results/checkpoints results/checkpoints"
echo "Nibi code at $(git rev-parse --short HEAD)"
