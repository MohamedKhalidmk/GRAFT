#!/bin/bash
#SBATCH --account=def-sylu_gpu
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH --time=08:00:00
#SBATCH --job-name=graft-qwen
#SBATCH --output=%x-%j.out
# GRAFT with Qwen instead of Haiku (llm.mode: local): starts vLLM serving Flotilla's Qwen3.8-27B W4A16 on this GPU
# (served name "qwen"), waits until healthy, then runs the given configs one after another (eval.queue). No API key,
# no API spend. The same GPU embeds the graph (bge-small, ~1 GB beside vLLM at 0.85 memory).
#   cd ~/projects/def-sylu/khaledmk/SGAR && sbatch scripts/fir/run_qwen_graft.sbatch configs/runs/exp/lh/c_qwen_trexfull_eig.yaml ...
set -euo pipefail
FLO=$HOME/projects/def-sylu/khaledmk/flotilla
MODEL=$HOME/scratch/flotilla/quant/qwen3.8-27b-w4a16
C=${SLURM_TMPDIR:-$HOME/scratch/flotilla/cache}
(
  source "$FLO/scripts/trillium/modules.sh"
  export HF_HUB_OFFLINE=1 VLLM_CACHE_ROOT="$C/vllm" TRITON_CACHE_DIR="$C/triton" TORCHINDUCTOR_CACHE_DIR="$C/inductor" \
         XDG_CACHE_HOME="$C" HUMMING_CACHE_DIR="$C/humming" HUMMING_TMP_DIR="$C/humming-tmp" FLASHINFER_WORKSPACE_BASE="$C"
  exec "$FLO/envs/flotilla/bin/vllm" serve "$MODEL" --served-model-name qwen --port 8000 --seed ${VLLM_SEED:-20261119} \
       --max-model-len 65536 --gpu-memory-utilization 0.85 --max-num-seqs 64 --reasoning-parser qwen3
) > "vllm-$SLURM_JOB_ID.log" 2>&1 &
VLLM=$!
trap 'kill $VLLM 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
  curl -sf http://127.0.0.1:8000/health >/dev/null && break
  kill -0 $VLLM 2>/dev/null || { echo "vLLM exited; see vllm-$SLURM_JOB_ID.log"; exit 2; }
  sleep 30
done
curl -sf http://127.0.0.1:8000/health >/dev/null || { echo "vLLM not healthy after 60 min"; exit 2; }
echo "[qwen] vLLM healthy $(date +%H:%M)"
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
export HF_HUB_OFFLINE=1 GRAFT_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
.venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}" "$@"
