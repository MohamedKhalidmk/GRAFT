| candidate | setup | run | arm | what | repeats | accuracy_mean | accuracy_sd | per_repeat | gold_in_final_facts | answers_cut_at_256_tokens_pct | calls_per_question | output_tokens_per_question |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G08 | S18 | run-01 | A | mode C, empty start | 3 | 39.3 | 2.3 | 42 / 38 / 38 | 50.7 | 35.3 | 1.0 | 118 |
| G35 | S66 | run-01 | B | the T-REx structure guide | 3 | 47.0 | 1.0 | 48 / 46 / 47 | 59.0 | 26.3 | 2.01 | 193 |
| G33 | S60 | run-01 | C v2 | working memory in the graph | 3 | 33.3 | 0.6 | 33 / 34 / 33 | 40.3 | 0.0 | 4.55 | 217 |
| G34 | S63 | run-01 | C- v2 | same steps, prompt only | 3 | 33.0 | 1.0 | 32 / 34 / 33 | 39.0 | 0.0 | 4.56 | 220 |
