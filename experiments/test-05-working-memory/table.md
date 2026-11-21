| model | arm | what | repeats | accuracy_mean | accuracy_sd | per_repeat | gold_in_final_facts | calls_per_question | input_tokens_per_question | output_tokens_per_question | cost_per_100_questions_usd | run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Haiku | A | mode C, one answer call | 3 | 34.7 | 0.6 | 35 / 34 / 35 | 50.7 | 1.0 | 2376 | 66 | 0.027 | runs/run-01/exp_wm_empty_a_modec_20261120-192124 |
| Haiku | B | question layer | 3 | 33.7 | 0.6 | 34 / 33 / 34 | 49.0 | 2.0 | 2937 | 147 | 0.037 | runs/run-01/exp_wm_empty_b_qlayer_20261120-192124 |
| Haiku | C | working memory in the graph | 3 | 35.3 | 1.2 | 34 / 36 / 36 | 43.0 | 4.54 | 6272 | 290 | 0.077 | runs/run-01/exp_wm_empty_c_wm_graph_20261120-192125 |
| Haiku | C- | same steps, prompt only | 3 | 32.7 | 1.2 | 34 / 32 / 32 | 41.7 | 4.51 | 6358 | 289 | 0.078 | runs/run-01/exp_wm_empty_cm_wm_prompt_20261120-192125 |
| Haiku | C v2 | C, step prompt with the newer-fact rule | 3 | 35.7 | 2.1 | 38 / 34 / 35 | 45.3 | 4.51 | 6428 | 311 | 0.08 | runs/run-02/exp_wm_empty_c_wm_graph_v2_20261121-011055 |
| Haiku | C- v2 | C-, same prompt | 3 | 33.0 | 0.0 | 33 / 33 / 33 | 41.3 | 4.52 | 6539 | 309 | 0.081 | runs/run-02/exp_wm_empty_cm_wm_prompt_v2_20261121-011059 |
| Haiku | A | mode C, rerun the same day as round 2 | 3 | 34.7 | 1.5 | 36 / 33 / 35 | 50.3 | 1.0 | 2377 | 63 | 0.027 | runs/run-02/exp_real_wm_empty_a_modec_rerun1121_20261121-011005 |
