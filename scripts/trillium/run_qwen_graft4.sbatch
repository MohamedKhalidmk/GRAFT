#!/bin/bash
#SBATCH --account=def-sylu
#SBATCH --nodes=1
#SBATCH --gpus-per-node=h100:4
#SBATCH --time=03:00:00
#SBATCH --job-name=graft-q4
#SBATCH --output=%x-%j.out
# GRAFT with Qwen on a whole Trillium GPU node (4 H100s): one vLLM server per GPU (Flotilla's Qwen3.8-27B W4A16,
# served name "qwen", port 8000+i), and one config per GPU run against its own server, all four at once. Free, offline.
# Submit from trig-login01 with --export=ALL (Trillium drops the environment otherwise), from $SCRATCH/sgar/SGAR:
#   cd $SCRATCH/sgar/SGAR && sbatch --export=ALL scripts/trillium/run_qwen_graft4.sbatch C1.yaml C2.yaml C3.yaml C4.yaml
# Up to 4 configs. A config named *_rK.yaml (one repeat per job, test 08 run-02) gets vLLM seed 20261119+K, like its
# Fir and Nibi twins (VLLM_SEED); others use 20261119. Each server and its run share one GPU (CUDA_VISIBLE_DEVICES), and
# each server compiles into its own cache folder: many servers compiling into one shared cache at the same moment hung
# or failed before (Nibi "Stale file handle" 2026-11-20; Fir Memory routes 2026-11-21).
set -euo pipefail
[[ $# -ge 1 && $# -le 4 ]] || { echo "give 1 to 4 configs"; exit 2; }
FLO=/project/def-sylu/khaledmk/flotilla
MODEL=$SCRATCH/flotilla/quant/qwen3.8-27b-w4a16
T=${SLURM_TMPDIR:-/dev/shm/graft-$SLURM_JOB_ID}
mkdir -p "$T"
ARGS=("$@")
PIDS=()
trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT
for i in $(seq 0 $(($# - 1))); do
  cfg=${ARGS[$i]}
  k=$(basename "$cfg" .yaml | sed -nE 's/.*_r([0-9]+)$/\1/p')
  seed=$((20261119 + ${k:-0}))
  C="$T/gpu$i"; mkdir -p "$C"
  (
    source "$FLO/scripts/trillium/modules.sh"
    export CUDA_VISIBLE_DEVICES=$i HF_HUB_OFFLINE=1 VLLM_CACHE_ROOT="$C/vllm" TRITON_CACHE_DIR="$C/triton" \
           TORCHINDUCTOR_CACHE_DIR="$C/inductor" XDG_CACHE_HOME="$C" HUMMING_CACHE_DIR="$C/humming" \
           HUMMING_TMP_DIR="$C/humming-tmp" FLASHINFER_WORKSPACE_BASE="$C" CUDA_CACHE_PATH="$C/nv"
    exec "$FLO/envs/flotilla/bin/vllm" serve "$MODEL" --served-model-name qwen --port $((8000 + i)) --seed $seed \
         --max-model-len 65536 --gpu-memory-utilization 0.85 --max-num-seqs 64 --reasoning-parser qwen3
  ) > "vllm-$SLURM_JOB_ID-gpu$i.log" 2>&1 &
  PIDS+=($!)
  echo "[qwen4] gpu $i: $cfg, seed $seed, port $((8000 + i))"
done
for i in $(seq 0 $(($# - 1))); do
  for n in $(seq 1 120); do
    curl -sf http://127.0.0.1:$((8000 + i))/health >/dev/null && break
    kill -0 "${PIDS[$i]}" 2>/dev/null || { echo "vLLM on gpu $i exited; see vllm-$SLURM_JOB_ID-gpu$i.log"; exit 2; }
    sleep 30
  done
  curl -sf http://127.0.0.1:$((8000 + i))/health >/dev/null || { echo "vLLM on gpu $i not healthy after 60 min"; exit 2; }
done
echo "[qwen4] all servers healthy $(date +%H:%M)"
source "$SLURM_SUBMIT_DIR/scripts/trillium/common.sh"
export HF_HUB_OFFLINE=1
RUNS=()
for i in $(seq 0 $(($# - 1))); do
  cfg=${ARGS[$i]}
  CUDA_VISIBLE_DEVICES=$i GRAFT_OPENAI_BASE_URL=http://127.0.0.1:$((8000 + i))/v1 \
    .venv/bin/python -m eval.queue --name "slurm_${SLURM_JOB_ID}_g$i" "$cfg" > "graft-q4-$SLURM_JOB_ID-gpu$i.log" 2>&1 &
  RUNS+=($!)
done
rc=0
for p in "${RUNS[@]}"; do wait "$p" || rc=1; done
echo "[qwen4] done $(date +%H:%M), rc $rc"
exit $rc
