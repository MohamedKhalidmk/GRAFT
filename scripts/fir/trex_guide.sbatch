#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH --time=03:00:00
#SBATCH --job-name=trex-guide
#SBATCH --output=%x-%j.out
# Test 06 step 0 (free, no LLM): T-REx structure guide + coverage of the question parses and document relations.
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1
B=$(ls -d $RESULTS_DIR/runs/exp_wm_empty_b_qlayer_2* | tail -1)
.venv/bin/python scripts/trex_guide.py --trex-dir $HOME/scratch/sgar/trex --labels my_method/wikidata_property_labels_250.json \
  --aliases my_method/wikidata_property_aliases_250.json \
  --docs results/checkpoints/shared_graphs/real_mh_262k_empty_start.json \
  --parses $B/repeat_0/predictions.jsonl --out results/checkpoints/trex_guide.json
