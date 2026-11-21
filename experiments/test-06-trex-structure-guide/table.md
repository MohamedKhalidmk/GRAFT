| model | arm | what | repeats | accuracy_mean | accuracy_sd | per_repeat | gold_in_final_facts | cost_per_100_questions_usd |
|---|---|---|---|---|---|---|---|---|
| Haiku | A | empty start, mode C (test 05, rerun the same day) | 3 | 34.7 | 1.5 | 36 / 33 / 35 | 50.3 | 0.027 |
| Haiku | B | T-REx as a structure guide (linking + planning) | 3 | 45.7 | 1.5 | 47 / 46 / 44 | 60.3 | 0.037 |
| Haiku | C | T-REx as a bridge (walk only, weight 0.2) | 3 | 17.3 | 1.2 | 18 / 16 / 18 | 32.0 | 0.022 |
| Haiku | D | C + 5 labelled background facts | 3 | 17.7 | 1.5 | 19 / 16 / 18 | 33.0 | 0.029 |
