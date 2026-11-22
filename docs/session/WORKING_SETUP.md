# Working setup: how we work on Flotilla and GRAFT

For a new Claude session picking up this project. The same file is in both repos (Flotilla `docs/session/WORKING_SETUP.md`,
GRAFT `docs/session/WORKING_SETUP.md`). No secrets are in it: no keys, passwords or tokens. Written 2026-11-21.

Companion documents: [PROJECT_HISTORY.md](PROJECT_HISTORY.md) (everything that happened and why),
[HANDOFF.md](HANDOFF.md) (what is running right now and the next steps), [STATUS.md](STATUS.md) (the Open experiments table), and Flotilla's
[PROTOCOL.md](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/PROTOCOL.md) (the frozen evaluation
rules, summarised below).

## 1. Repos and branches

| Repo | Local folder | Work branch | Notes |
|---|---|---|---|
| Flotilla (github.com/MohamedKhalidmk/Flotilla) | /Users/mk/flotilla | `restructure` | not merged into main yet |
| GRAFT (github.com/MohamedKhalidmk/GRAFT) | /Users/mk/SGAR | `graft-linking-hybrid` | `main` has the restyle (PR #6); research continues on the branch. Never push to `main` without the user's go |

GRAFT was called SGAR during development; folders and some file names keep that name.

## 2. Connecting to the clusters

All three are Digital Research Alliance of Canada clusters. User `khaledmk`, key `~/.ssh/id_ed25519`, groups
`def-sylu` (`def-sylu_cpu`, `def-sylu_gpu` accounts on Fir and Nibi).

**Use the ControlMaster sockets.** `~/.ssh/config` has `ControlMaster auto`, `ControlPath ~/.ssh/cm-%r@%h:%p`,
`ControlPersist 8h` (shown for `Host fir`). Every command from the Mac goes through an open socket, without prompting:

```bash
ssh -o BatchMode=yes -o ControlPath=$HOME/.ssh/cm-%r@%h:%p khaledmk@fir.alliancecan.ca 'squeue -u $USER'
```

Same for `nibi.alliancecan.ca` and `trillium.alliancecan.ca`. In zsh, unquoted variables do not split into words:
wrap ssh in a function (`F(){ ssh -o BatchMode=yes -o ControlPath=... khaledmk@fir.alliancecan.ca "$@"; }`) and use
bash scripts for loops over job lists.

**Duo logins.** When a socket has expired, `BatchMode` fails with a permission error. Do not try to log in yourself:
ask the user to open the socket once in a terminal (`ssh khaledmk@fir.alliancecan.ca`, then approve Duo), and say
which cluster. After that the socket lasts 8 hours.

| Cluster | Use it for | Limits |
|---|---|---|
| **Fir** | the main cluster: CPU and GPU (H100) jobs, all data, paid Haiku runs | project filesystem is slow to import from: jobs unpack the venv to local disk (section 4) |
| **Nibi** | twins of Fir jobs; CPU, full H100 and MIG slices (`nvidia_h100_80gb_hbm3_3g.40gb`, `2g.20gb`, `1g.10gb`) | the group's full-H100 fairshare is low (starts can take days); 3g.40gb slices start fast |
| **Trillium** | free CPU runs only (whole 192-core nodes, account `def-sylu`) | **compute nodes have no internet**, so no paid (API) runs; home and /project are read-only on compute nodes; GPU jobs only from `trig-login01`, which has no socket here; `sbatch` needs `--export=ALL` to pass environment variables |

Fir cannot ssh to Nibi or Trillium directly: copy between clusters by streaming through the Mac
(`ssh fir 'tar cf - ...' | ssh nibi 'tar xf - -C ...'`), never storing large files on the Mac. When copying from the Mac with tar, set `COPYFILE_DISABLE=1`: macOS tar otherwise adds `._*` files, which broke the session-docs test on Fir once (2026-11-22).

## 3. Where things live

**GRAFT (SGAR)**

| What | Fir | Nibi | Trillium |
|---|---|---|---|
| Code (an rsync copy, not a git checkout) | `~/projects/def-sylu/khaledmk/SGAR` | same path (synced by `scripts/nibi/sync_code.sh`) | `/scratch/khaledmk/sgar/SGAR` (`scripts/trillium/sync_code.sh`) |
| Venv archive | `$HOME/scratch/sgar/venv.tar` (packed by `scripts/fir/pack_venv.sh`) | `~/scratch/sgar/venv.tar` | `/scratch/khaledmk/sgar/venv.tar` |
| Results and runs | `$HOME/scratch/sgar/results/runs/` | `~/scratch/sgar/results/` | `/scratch/khaledmk/sgar/results/` |
| Graphs | `results/checkpoints/shared_graphs/real_mh_262k_empty_start.json` (document graph), `real_mh_262k_trexfull_link_start.json` (full T-REx, 1.7 GB) | copied, md5-checked | copied |
| Saved node vectors | `<graph>.emb.npy` and `<graph>.emb.texts.json` next to the graph (`scripts/embed_graph.py`) | copied | copied |
| T-REx guide | `results/checkpoints/trex_guide.json` (`scripts/fir/trex_guide.sbatch`) | copied | copied |
| Raw T-REx | `$HOME/scratch/sgar/trex/*.parquet` | | |
| HF cache (bge-small, datasets) | `$HOME/scratch/sgar/hf` | `~/scratch/sgar/hf` | copied |
| Job logs | `<job-name>-<jobid>.out` in the code folder | same | same |

Fir's code copy is synced from the Mac with `rsync -aR <files> khaledmk@fir.alliancecan.ca:projects/def-sylu/khaledmk/SGAR/`.
It is not a git checkout, and `git archive` leaves out the two submodules (`baselines/memoryagentbench`,
`my_method/gnn/GOAt`): copy those too.

**Flotilla**

| What | Fir | Nibi |
|---|---|---|
| Code | `~/projects/def-sylu/khaledmk/flotilla` | `/project/def-sylu/khaledmk/flotilla` |
| vLLM env | `envs/flotilla` in the code folder (vLLM 0.32) | same |
| Qwen3.8-27B W4A16 | `$HOME/scratch/flotilla/quant/qwen3.8-27b-w4a16` | `~/scratch/flotilla/quant/...` |
| HF cache | `$SCRATCH/flotilla/hf` | |
| Route labels | `$SCRATCH/flotilla/test04-labels/run-03` (pool); new LongMemEval merge goes to `run-04-lme` | |
| LongMemEval | `$HOME/scratch/flotilla/data/longmemeval/` (items, split, token counts), runs in `$SCRATCH/flotilla/lme/` | `~/scratch/flotilla/lme/` |

## 4. How jobs run

- **Local-disk venv.** Imports from the project filesystem took 7 to 30+ minutes per process. Every GRAFT job sources
  `scripts/<cluster>/common.sh`, which copies the code to `$SLURM_TMPDIR`, unpacks `venv.tar` there (about 15-35 s),
  installs `openai` from the Alliance wheelhouse if missing (offline), and links `results/`, `data/`, `envs/`.
- **Paid runs** use `scripts/fir/run_real_guarded_cpu.sbatch` (CPU) or `run_real_guarded.sbatch` (GPU), with the
  configs as arguments; free Qwen runs use `scripts/fir/run_qwen_graft.sbatch` (starts vLLM, waits for health, runs
  the queue). Nibi has the same scripts in `scripts/nibi/`.
- **Twins.** Submit each pass as a CPU and a GPU job (and on Nibi when useful). The first to start wins; cancel the
  others at once. Helpers (in the session scratchpad, rewrite if gone): `twin_pair.sh JOB_A JOB_B` on Fir,
  `twin_xc.sh FIR_JOB NIBI_JOB` across clusters. Run folders carry the job id and an owner file, so two twins of one
  config never share a folder, and only the same Slurm job (a requeue) resumes an unfinished folder: a rerun always
  gets a new folder named after its own job (`eval/run.py`, 2026-11-21).
- **Time limits** = measured runtime +50%. Use a pilot to measure before submitting long runs.
- **Watchers.** Wait for jobs with a background shell loop that polls `squeue` and prints results when the jobs leave
  the queue; never poll with foreground sleeps.
- **Never overwrite runs.** A rerun is a new run folder and, in the experiments, a new `run-NN` plus a Revisions line.
- **Results into the repo.** Copy only small per-run files (config.yaml, summary.json, scored.jsonl, usage.jsonl) into
  `experiments/test-NN-*/runs/run-NN/`, then `make_table.py` builds table.csv, table.md and figure.png. In GRAFT,
  `scripts/build_figures.sh` rebuilds every table, figure and `assets/results.png`.

## 5. API keys and spend

- The Anthropic key **only** goes through a hidden macOS dialog piped straight into ssh, read into the submitting
  shell's environment, and passed to the job by sbatch:
  ```bash
  osascript -e 'text returned of (display dialog "..." default answer "" with hidden answer ...)' \
    | ssh ... khaledmk@fir.alliancecan.ca 'read -r ANTHROPIC_API_KEY; export ANTHROPIC_API_KEY COST_CAP_USD=1; cd ...; sbatch ...'
  ```
  Never in chat, files, logs or commands. If the user enters nothing, nothing is submitted; say so.
- **Cost guard.** The guarded scripts add up `cost_usd` from the usage logs of the job's own runs (by run_name) every
  minute and stop the job past `COST_CAP_USD` (we use $1 per job).
- **Fixed Haiku check (canary).** Every paid Haiku batch starts with a one-repeat replay of the 2026-11-13 run's exact
  facts (`configs/runs/exp/canary/haiku_replay38.yaml`, about $0.027); `CANARY=0` skips it (use it on twins and on a
  second job in the same batch). History: GRAFT `experiments/test-07-haiku-drift/haiku_canary.md`. Haiku drifted
  (identical prompts 38 then about 34), so **compare methods only within the same day**.
- **Ask before** spending more than a few dollars. Log every dollar in Flotilla `docs/reference/run_log.md` (dated entry plus the
  spend table and running total).

## 6. Working rules

- Heavy work never on the user's Mac: graph builds, PageRank, embeddings, grading, PDF builds of big reports all run
  as cluster CPU jobs. The Mac is for editing code, small unit tests and git. If a cluster needs a login, ask.
- Docs: `docs/reference/` (PROTOCOL, REGISTRY, run log), `docs/session/` (this file, HANDOFF, STATUS, PROJECT_HISTORY), `docs/design/`.
  The session files are edited only in Flotilla's `docs/session/`, then `python scripts/sync_session_docs.py` copies them to
  GRAFT and writes `scripts/SHA256SUMS`; `tests/test_session_docs.py` in each repo fails if a copy drifts. Markdown only:
  a PDF is built (WeasyPrint on Fir) only when the user asks for one.
- Commits are authored by the user only: **no Co-Authored-By or any Claude attribution line**, in commits or PRs.
  Don't rewrite history.
- Numbered tests: `experiments/test-NN-name/` with README (Question, Setup, Result, Decision, Revisions), config,
  runs, table and figure; linked from `experiments/INDEX.md`. Designs go in `docs/design/` before code.
- Preview before merging: send a rendered preview and wait for the user's go before merging into `main`.
- Log every decision with a one-line reason, and every dollar, in Flotilla `docs/reference/run_log.md`.
- Report only finishes, failures and decisions; no progress chatter. Give a time range before each step.
- GRAFT presets: a GRAFT change that wins (writer v2, the chat guide, adaptive retrieval, ...) becomes a named preset with its G ID in `flotilla/memory_route.py` (`GRAFT_PRESETS`, `GRAFT_PRESET_IDS`) before any Memory route uses it; route configs pick a preset and override only runtime keys. `tests/test_memory_route.py::test_graft_config_is_a_named_preset` enforces it (user, 2026-11-22).
- Every report starts with "Status changes": each row of [STATUS.md](STATUS.md)'s Open experiments table that changed since the last report, old state to new state, with the reason, one line each (or "no changes"). Update the table with every report; never delete a row; never change a state without listing it. Dropping, parking or reverting anything needs the user's yes first and a run-log line with the reason (user, 2026-11-22).
- Decide routine things and report after; ask only for scope, model, benchmark or rule changes, or anything risky or
  costly. Don't drop a model without logging why.
- Writing style for docs: plain reflective sentences, commas, no em dashes.
- Every always-wrong question gets one label: verifier bug, grader bug, wrong gold, or model wrong.
- Metrics match the comparison (user, 2026-11-21): substring match for MemoryAgentBench and for choosing between GRAFT
  variants; a strict metric only where the benchmark or paper we compare against is strict.

## 7. Flotilla's protocol (summary)

Full text: [PROTOCOL.md](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/PROTOCOL.md). It fixes, before
any scored run, what is measured, how, and how components are chosen, so no choice is made after seeing test results.
Each version is a git tag; results say which version they ran under.

Frozen decision rules:
- **4.1 Quantization:** MATH-500 (all 500); choose 4-bit if it is at most 1.0 point below 8-bit, else 8-bit.
  Applied 2026-11-20: BF16 0.978, FP8 0.984, our W4A16 (GPTQ) 0.984, so Qwen is served as W4A16.
- **4.2 Command A+:** keep only if Command A+ alone beats Qwen alone on the small test by a clear margin (paired
  bootstrap lower bound above 0). Result: Command A+ minus Qwen = -0.104, 95% CI [-0.143, -0.066]: dropped.
  (4.2b Phi was replaced by gpt-oss-20b in v9; v10 dropped gpt-oss: router B's gain over Qwen alone, +0.4, was under
  the 1-point bar.)
- **Router keep rule (test 04):** keep a router if it is within 1 point of the best fixed route (Vote) at lower
  compute, or more than 1 point better; otherwise use the best fixed route. Dev tuning keeps a 0.5-point margin.
- Also: 4.3 EiG-Search vs GOAt, 4.4 voting N (smallest N within 0.5 points of the best), 4.5 router A vs B.

Version history: v1 frozen 2026-11-19; v2 verifier retry; v3 leakage template rule; v4 router A implementation; v5 the
Command A+ rule; v6 Command A+ native tools; v7 tool-loop budget note; v8 Command A+ from local FP8; v9 Phi dropped for
gpt-oss-20b (plus addenda on native tools); v10 (2026-11-20) gpt-oss dropped, Qwen3.8-27B W4A16 alone. Later changes
are test 04 decisions logged in the run log (route set, labels, routers). PROTOCOL.md's status line names protocol-v10
(fixed 2026-11-21), and the v10 addendum (2026-11-21) makes Claude Haiku 5.5 the LongMemEval judge.

How a change is made: only before the result it affects exists; a new version number, a dated changelog entry in
PROTOCOL.md saying what changed, why and who decided, a git tag `protocol-vN`, and a run-log entry. Results already
scored are never re-scored under a new rule without saying so.

## 8. First 10 minutes in a new session

1. Read [STATUS.md](STATUS.md) (open experiments) and [HANDOFF.md](HANDOFF.md) (running jobs, broken things, next steps), then this file, then skim
   PROJECT_HISTORY.md parts 1 and 11.
2. `git pull` in /Users/mk/flotilla (`restructure`) and /Users/mk/SGAR (`graft-linking-hybrid`); check `git status` for
   other sessions' uncommitted files and don't commit them.
3. Read the last 30 lines of Flotilla `docs/reference/run_log.md` (latest decisions and spend).
4. Test the sockets: `ssh -o BatchMode=yes -o ControlPath=... khaledmk@fir.alliancecan.ca 'hostname'` (and nibi). If one
   fails, ask the user to log in with Duo.
5. `squeue -u $USER` on Fir and Nibi; compare with HANDOFF.md's job list.
6. For each finished job, collect results (watchers from the old session are gone).
7. Check `experiments/INDEX.md` in both repos for test status.
8. Check memory files in `~/.claude/projects/-Users-mk-SGAR/memory/` (MEMORY.md index) for the user's standing rules.
9. Don't submit paid runs until the user has entered a key through the dialog; free Qwen runs need no key.
10. Tell the user in two or three lines what is running, what finished, and the next step, then continue.
