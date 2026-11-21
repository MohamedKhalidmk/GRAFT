# Handoff (2026-11-21, end of session)

For a new session starting cold. Same file in both repos (`docs/HANDOFF.md`). Commands use the ControlMaster sockets
(`ssh -o BatchMode=yes -o ControlPath=$HOME/.ssh/cm-%r@%h:%p khaledmk@<fir|nibi>.alliancecan.ca '...'`); below,
`F '...'` means that ssh to Fir and `N '...'` to Nibi. The watchers and helper agents of the old session are gone:
nothing is watching these jobs now.

## 1. Jobs running or queued

| Cluster | Job ID | What | Output | Check |
|---|---|---|---|---|
| Fir | 4874611 (done) | GRAFT test 06 **arm E**: T-REx guide + working memory in the graph (C v2), Haiku, 3 repeats, after the fixed Haiku check; cap $1 | `$HOME/scratch/sgar/results/runs/exp_real_tg_e_guide_wm_v2_*_j4874611/`, `exp_real_canary_replay38_*_j4874611/`; log `~/projects/def-sylu/khaledmk/SGAR/tg-e_guide_wm_v2-cpu-4874611.out` | `F 'sacct -j 4874611 -X -o State,Elapsed'`, then score with the snippet below |
| Fir | 4876819 (pending) | GRAFT on **Qwen** (free): mode C, the guide, C v2, C- v2 on the empty-start graph (`configs/runs/exp/qwen/*.yaml`) | `$HOME/scratch/sgar/results/runs/exp_qwen_empty_*`; log `graft-q-all-4876819.out` and `vllm-4876819.log` in the SGAR folder | `F 'squeue -j 4876819'`. **Twin of Nibi 28263641: when one starts RUNNING, `scancel` the other** |
| Nibi | 28263641 (pending) | same Qwen job on a 3g.40gb MIG slice | `~/scratch/sgar/results/runs/exp_qwen_empty_*` | `N 'squeue -j 28263641'` |
| Nibi | 28262994-28263014, 28263382-28263401 | Flotilla **LongMemEval Fast** route, shards 01-19 (many running, 04-09 pending) | `~/scratch/flotilla/lme/runs/fast/lme_KK/` (trace.jsonl, compute.json) | `N 'squeue -u $USER'`; Fir twins of these (4875345-53) may exist: cancel any twin whose partner runs |
| Nibi | 28261677, 28261678, 28261679 (running), 28261680, 28261681 (pending) | LongMemEval shard 00 pilot on MIG: Tools, Deep, Deep+Tools, Vote, Vote+Tools | `~/scratch/flotilla/lme/runs/<route>/lme_00_mig/` | `N 'squeue -u $USER'` |
| Nibi | 28263147 (running) | GRAFT build pilot (5 LongMemEval histories, guide preset) on MIG | `~/scratch/flotilla/lme/graft_cache/`, `runs/prepare/` | look for `prepare-28263147.json`; if it failed on `openai`, see 2b |

Score a GRAFT run (on Fir): `F 'cd $HOME/scratch/sgar/results/runs; for p in <run>/repeat_*/scored.jsonl; do python3 -c "import json,sys; s=[json.loads(l) for l in open(sys.argv[1])]; print(sum(x[\"substring_exact_match\"]>0 for x in s), sum(bool(x[\"answer_in_retrieved\"]) for x in s), round(sum(x.get(\"cost_usd\",0) for x in s),3))" $p; done'`

Arm E (4874611) and the guide rerun (4874613) finished and are recorded in GRAFT test 06 run-03.

## 2. Half-done or broken

a. **openai missing from GRAFT's venv** (GRAFT on Qwen failed: Nibi 28252727, $0). Done: `scripts/{fir,nibi,trillium}/common.sh`
   install it from the Alliance wheelhouse when missing (GRAFT 188c223, synced to Fir and Nibi), and Flotilla's
   `scripts/fir/lme_job.sbatch` does the same for the Memory-route GRAFT bridge (synced to Fir and Nibi). Left: **not yet
   verified on a compute node**. Check the first lines of `graft-q-all-<job>.out` once 4876819 or 28263641 starts. A
   permanent fix is to repack the venv with openai: `F 'cd ~/projects/def-sylu/khaledmk/SGAR && .venv/bin/pip install --no-index openai && sbatch scripts/fir/pack_venv.sh'` (then copy venv.tar to Nibi and Trillium).
b. **LongMemEval GRAFT build pilot 28263147** may have started before the lme_job.sbatch fix. If it failed, resubmit:
   `bash scripts/fir/submit_longmemeval.sh prepare 1:00:00 00 -- --limit 5` (on Nibi with
   `EXTRA_SBATCH=--gpus-per-node=nvidia_h100_80gb_hbm3_3g.40gb:1`; see the script header).
c. **LongMemEval judge: decided (user, 2026-11-21): Claude Haiku 5.5** with LongMemEval's official judge prompts, the fixed
   Haiku check before each judge batch, request IDs logged (PROTOCOL.md, protocol-v10 addendum). Left: add the Haiku
   backend to `memory_route judge` with a cost guard (paid, CPU job, key via the dialog only), and put the canary job
   before it in `submit_longmemeval.sh judge`. Estimated $2.50 for ten routes plus the checks; ask before running.
d. Arm E and the guide rerun are recorded (test 06 run-03): E 46.7, guide alone 46.7 the same day; E not kept.
e. **Per-row cost order** (cheapest route judged per question from its own GPU-seconds) was asked of the labelling agent
   for `strategy_labels.py` and `strategy_router.py`; check `git log` in Flotilla for whether it landed, and add it with
   tests if not.
f. PROTOCOL.md's status line now names protocol-v10 (fixed 2026-11-21).

## 3. Next three steps

1. **Finish LongMemEval route labels** (Flotilla, Fir or Nibi; all free on local Qwen):
   - the six base routes on all 20 shards: `bash scripts/fir/submit_longmemeval.sh base <route> <time> 00 01 ... 19`
   - GRAFT graphs: `submit_longmemeval.sh prepare <time> <shards>`
   - the four Memory routes: `submit_longmemeval.sh memory <route> <time> <shards>`
   - grading with Haiku: `submit_longmemeval.sh judge <time> <name>` (after 2c; paid, key via the dialog)
   - merge into new labels:
     `python -m flotilla.strategy_labels --pool-labels $SCRATCH/flotilla/test04-labels/run-03 --memory-items $SCRATCH/flotilla/data/longmemeval/memory_items.jsonl --verdicts <judge>/verdicts.jsonl --memory-split $SCRATCH/flotilla/data/longmemeval/split.json --runs <route>=<dirs> ... --build-runs $LME/runs/prepare/* --graft-cache $LME/graft_cache --out $SCRATCH/flotilla/test04-labels/run-04-lme`
   Base routes and GRAFT run on 3g.40gb MIG slices (full H100s queue for days); time limits from the pilot +50%.
2. **Train the four supervised routers once on all ten routes:**
   `LABELS=$SCRATCH/flotilla/test04-labels/run-04-lme bash scripts/fir/submit_strategy_router.sh train <name>`
   (compare against Vote, 0.5-point dev margin; held-out only at the end with `--held-out`).
3. **Live RL from the best router:** `bash scripts/fir/submit_rl_router.sh train <name>` with `LABELS`, `ROUTER_DIR`
   (the step-2 output), `POOL` and `AUDIT` set (the pool file with gold answers and run-03's `audit/` are not on Fir
   yet: copy them first). Track questions solved that every fixed route missed (wrong-gold excluded).

## 4. Documents

| Document | Flotilla (`restructure`) | GRAFT (`graft-linking-hybrid`) |
|---|---|---|
| Working setup (clusters, jobs, keys, rules, first 10 minutes) | `docs/WORKING_SETUP.md` / `.pdf` | `docs/WORKING_SETUP.md` / `.pdf` |
| Project history (every test, decision, bug, spend, lessons) | `docs/PROJECT_HISTORY.md` / `.pdf` | `docs/PROJECT_HISTORY.md` / `.pdf` |
| Protocol (frozen evaluation rules) | `docs/PROTOCOL.md` | link: github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/PROTOCOL.md |
| Run log (every decision and dollar) | `docs/run_log.md` | |
| Experiments | `experiments/INDEX.md` | `experiments/INDEX.md` |
