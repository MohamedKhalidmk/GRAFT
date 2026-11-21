# Sourced by every Nibi job script: modules, environment, scratch paths. Not run on its own.
# Same layout as Fir (scripts/fir/common.sh): code in the group project space, everything big on scratch.
# Nibi has no .venv in the code dir: jobs always unpack $SCRATCH_ROOT/venv.tar (packed on Fir from .venv, python 3.12
# from the shared CVMFS stack) to the node's local disk.
module load StdEnv/2023 gcc python/3.12 arrow/25.0.0  # arrow provides pyarrow, which pip cannot install here
export REPO="${REPO:-$HOME/projects/def-sylu/khaledmk/SGAR}"
export SCRATCH_ROOT="$HOME/scratch/sgar"
export HF_HOME="$SCRATCH_ROOT/hf"            # model weights and datasets
export RESULTS_DIR="$SCRATCH_ROOT/results"   # runs, checkpoints, tables
export TIKTOKEN_CACHE_DIR="$SCRATCH_ROOT/tiktoken"
export PYTHONPATH="$REPO" PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
mkdir -p "$HF_HOME" "$RESULTS_DIR" "$TIKTOKEN_CACHE_DIR"
# Run from the node's local disk: the code is copied there and the venv unpacked from one archive on scratch.
# results/ and data/ stay where they are (linked); $REPO/results/checkpoints links to $SCRATCH_ROOT/results/checkpoints.
if [[ -n "${SLURM_JOB_ID:-}" && -n "${SLURM_TMPDIR:-}" && "${GRAFT_LOCAL:-1}" == 1 ]]; then
  [[ -f "$SCRATCH_ROOT/venv.tar" ]] || { echo "missing $SCRATCH_ROOT/venv.tar (copy it from Fir)"; exit 2; }
  t0=$(date +%s); L="$SLURM_TMPDIR/SGAR"; mkdir -p "$L"
  # job logs (*.out) of other running jobs are written into this folder while it is copied: skip them, and accept tar's
  # exit 1 ("file changed as we read it"), as in scripts/fir/common.sh (Fir job 4832774 failed on it before it started)
  (cd "$REPO" && tar cf - --warning=no-file-changed --exclude='./*.out' --exclude=./.venv --exclude=./envs \
     --exclude=./results --exclude=./data --exclude=./.git . || [[ $? == 1 ]]) | tar xf - -C "$L"
  for d in results data envs; do [[ -e "$REPO/$d" ]] && ln -sfn "$REPO/$d" "$L/$d"; done
  tar xf "$SCRATCH_ROOT/venv.tar" -C "$L"
  export REPO="$L" PYTHONPATH="$L" GRAFT_CORE_PYTHON="$L/.venv/bin/python"
  echo "[local] code and venv on $SLURM_TMPDIR in $(( $(date +%s) - t0 )) s"
fi
cd "$REPO"
