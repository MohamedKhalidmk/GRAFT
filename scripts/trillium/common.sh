# Sourced by every Trillium job script: modules, environment, scratch paths. Not run on its own.
# Trillium differs from Fir: $HOME and /project are read-only on compute nodes, so the code, the venv archive and all
# results live on scratch (/scratch/khaledmk/sgar). Submit from $REPO so the job's .out file lands on scratch too.
# CPU jobs only: GPU jobs must be submitted from trig-login01, which these scripts do not cover.
module load StdEnv/2023 gcc python/3.12 arrow/25.0.0  # arrow provides pyarrow, which pip cannot install here
export SCRATCH_ROOT="${SCRATCH:-/scratch/$USER}/sgar"
export REPO="${REPO:-$SCRATCH_ROOT/SGAR}"
export HF_HOME="$SCRATCH_ROOT/hf"            # model weights and datasets
export RESULTS_DIR="$SCRATCH_ROOT/results"   # runs, checkpoints, tables
export TIKTOKEN_CACHE_DIR="$SCRATCH_ROOT/tiktoken"
export PYTHONPATH="$REPO" PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
mkdir -p "$HF_HOME" "$RESULTS_DIR" "$TIKTOKEN_CACHE_DIR"
# Run from node-local storage: the code is copied there and the venv unpacked from one archive on scratch.
# results/ and data/ stay where they are (linked); $REPO/results/checkpoints links to $SCRATCH_ROOT/results/checkpoints.
if [[ -n "${SLURM_JOB_ID:-}" && "${GRAFT_LOCAL:-1}" == 1 ]]; then
  [[ -f "$SCRATCH_ROOT/venv.tar" ]] || { echo "missing $SCRATCH_ROOT/venv.tar (copy it from Fir)"; exit 2; }
  T="${SLURM_TMPDIR:-/tmp/graft-$SLURM_JOB_ID}"  # Trillium nodes have no local disk: SLURM_TMPDIR is in /dev/shm (RAM)
  [[ -z "${SLURM_TMPDIR:-}" ]] && trap 'rm -rf "$T"' EXIT
  t0=$(date +%s); L="$T/SGAR"; mkdir -p "$L"
  # job logs (*.out) of other running jobs are written into this folder while it is copied: skip them, and accept tar's
  # exit 1 ("file changed as we read it"), as in scripts/fir/common.sh (Fir job 4832774 failed on it before it started)
  (cd "$REPO" && tar cf - --warning=no-file-changed --exclude='./*.out' --exclude=./.venv --exclude=./envs \
     --exclude=./results --exclude=./data --exclude=./.git . || [[ $? == 1 ]]) | tar xf - -C "$L"
  for d in results data envs; do [[ -e "$REPO/$d" ]] && ln -sfn "$REPO/$d" "$L/$d"; done
  tar xf "$SCRATCH_ROOT/venv.tar" -C "$L"
  export REPO="$L" PYTHONPATH="$L" GRAFT_CORE_PYTHON="$L/.venv/bin/python"
  # the gateway's local (vLLM/Qwen) backend needs openai, which the packed venv lacks (job 28252727 failed on it):
  # install it from the Alliance wheelhouse (offline) when missing
  "$L/.venv/bin/python" -c "import openai" 2>/dev/null || "$L/.venv/bin/python" -m pip install -q --no-index openai \
    || echo "[local] WARNING: openai not installable; llm.mode local will fail"
  export MPLCONFIGDIR="$T/mpl" XDG_CACHE_HOME="$T/cache"  # home is read-only here
  echo "[local] code and venv on $T in $(( $(date +%s) - t0 )) s"
fi
# Trillium compute nodes have no internet: outside connections hang until they time out (nltk.download('punkt') in
# memoryagentbench's utils stalled each run ~8 min on 2026-11-21). Point web traffic at a closed local port so it fails
# at once; the local gateway (127.0.0.1) is exempt. The data (HF cache, ~/nltk_data, tiktoken) is already local.
if [[ -n "${SLURM_JOB_ID:-}" && "${GRAFT_NO_NET:-1}" == 1 ]]; then
  export http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 \
         no_proxy=127.0.0.1,localhost NO_PROXY=127.0.0.1,localhost
fi
cd "$REPO"
