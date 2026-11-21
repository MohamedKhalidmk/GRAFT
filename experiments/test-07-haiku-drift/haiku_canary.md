# Fixed Haiku check

The same 100 prompts every time (the 2026-11-13 run's retrieved facts, configs/runs/exp/canary/). Built by scripts/haiku_canary.py.

| When | Run | Right (of 100) | Mean output tokens | Replies identical to the 2026-11-13 run | Request IDs logged |
|---|---|---|---|---|---|
| 2026-11-13 11:54 | exp_c_real_mh_262k_ans256_20261113-115012/repeat_0 | 38 | 63.0 | 100 | 0 |
| 2026-11-21 01:04 | exp_real_replay38_20261121-010340/repeat_0 | 34 | 65.0 | 29 | 0 |
| 2026-11-21 01:06 | exp_real_replay38_20261121-010340/repeat_1 | 36 | 66.3 | 29 | 0 |
| 2026-11-21 01:08 | exp_real_replay38_20261121-010340/repeat_2 | 33 | 60.0 | 33 | 0 |
| 2026-11-21 06:02 | exp_real_canary_replay38_20261121-022014/repeat_0 | 36 | 68.5 | 27 | 100 |
| When | Run | Right (of 100) | Mean output tokens | Replies identical to the 2026-11-13 run | Request IDs logged |
|---|---|---|---|---|---|
| 2026-11-13 11:54 | exp_c_real_mh_262k_ans256_20261113-115012/repeat_0 | 38 | 63.0 | 100 | 0 |
| 2026-11-21 01:04 | exp_real_replay38_20261121-010340/repeat_0 | 34 | 65.0 | 29 | 0 |
| 2026-11-21 01:06 | exp_real_replay38_20261121-010340/repeat_1 | 36 | 66.3 | 29 | 0 |
| 2026-11-21 01:08 | exp_real_replay38_20261121-010340/repeat_2 | 33 | 60.0 | 33 | 0 |
| 2026-11-21 06:02 | exp_real_canary_replay38_20261121-022014/repeat_0 | 36 | 68.5 | 27 | 100 |
