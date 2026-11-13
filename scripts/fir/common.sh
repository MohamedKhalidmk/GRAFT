# Sourced by every Fir job script: modules, environment, scratch paths. Not run on its own.
module load StdEnv/2023 gcc python/3.12 arrow/25.0.0  # arrow provides pyarrow, which pip cannot install here
export REPO="${REPO:-$HOME/projects/def-sylu/khaledmk/SGAR}"  # code lives under the group project space
export SCRATCH_ROOT="$HOME/scratch/sgar"
export HF_HOME="$SCRATCH_ROOT/hf"            # model weights and datasets
export RESULTS_DIR="$SCRATCH_ROOT/results"   # runs, checkpoints, tables
export TIKTOKEN_CACHE_DIR="$SCRATCH_ROOT/tiktoken"
export PYTHONPATH="$REPO" PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
mkdir -p "$HF_HOME" "$RESULTS_DIR" "$TIKTOKEN_CACHE_DIR"
cd "$REPO"
