| kind | variant | repeats | accuracy_mean | accuracy_sd | per_repeat | gold_in_final_facts | cost_per_100_questions_usd | run |
|---|---|---|---|---|---|---|---|---|
| reference | Mode C with GOAt, 2026-11-13 (test 01) | 1 | 38.0 | 0 | 38 | 51.0 | 0.027 | ../test-01-read-order/runs/run-02/exp_c_real_mh_262k_ans256_20261113-115012 |
| reference | Mode A with GOAt, 2026-11-13 (test 01) | 1 | 37.0 | 0 | 37 | 51.0 | 0.027 | ../test-01-read-order/runs/run-02/exp_a_real_mh_262k_ans256_20261113-112253 |
| paid | Mode A, EiG instead of GOAt | 1 | 36.0 | 0 | 36 | 49.0 | 0.027 | runs/run-01/exp_a_real_mh_262k_ans256_eig_20261120-001456 |
| paid | 50/50 hybrid with embedding search, GOAt | 3 | 32.0 | 2.6 | 34 / 29 / 33 | 55.0 | 0.027 | runs/run-01/exp_c_real_mh_262k_ans256_hybrid_goat_20261120-011749; runs/run-01/exp_c_real_mh_262k_ans256_hybrid_goat_20261120-012418; runs/run-01/exp_c_real_mh_262k_ans256_hybrid_goat_20261120-012430 |
| paid | 50/50 hybrid with embedding search, EiG | 3 | 32.0 | 2.0 | 32 / 30 / 34 | 54.0 | 0.027 | runs/run-01/exp_c_real_mh_262k_ans256_hybrid_eig_20261120-011758; runs/run-01/exp_c_real_mh_262k_ans256_hybrid_eig_20261120-012418; runs/run-01/exp_c_real_mh_262k_ans256_hybrid_eig_20261120-012447 |
| paid | Top-10 hybrid, EiG | 3 | 31.0 | 2.0 | 33 / 31 / 29 | 53.7 | 0.027 | runs/run-01/exp_c_real_mh_262k_ans256_topk10_eig_20261120-031120; runs/run-01/exp_c_real_mh_262k_ans256_topk10_eig_20261120-031218; runs/run-01/exp_c_real_mh_262k_ans256_topk10_eig_20261120-032428 |
| paid | Question graph (Haiku parses the question), EiG | 3 | 37.0 | 2.0 | 39 / 37 / 35 | 50.3 | 0.037 | runs/run-01/exp_c_real_mh_262k_ans256_qgraph_eig_20261120-032428 |
| free check | Mode C, EiG (free-check baseline) | 1 |  |  |  | 51.0 | 0 | runs/run-01/exp_c_fake_mh_262k_base_eig_20261120-004555 |
| free check | Mode A, EiG | 1 |  |  |  | 49.0 | 0 | runs/run-01/exp_a_fake_mh_262k_eig_check_20261119-235603 |
| free check | Embedding entity linking (k=5), EiG | 1 |  |  |  | 22.0 | 0 | runs/run-01/exp_c_fake_mh_262k_link_eig_20261120-004753 |
| free check | Embedding entity linking (k=5), GOAt | 1 |  |  |  | 25.0 | 0 | runs/run-01/exp_c_fake_mh_262k_link_goat_20261120-004753 |
| free check | Linking + hybrid, EiG | 1 |  |  |  | 34.0 | 0 | runs/run-01/exp_c_fake_mh_262k_both_eig_20261120-004555 |
| free check | Linking + hybrid, GOAt | 1 |  |  |  | 35.0 | 0 | runs/run-01/exp_c_fake_mh_262k_both_goat_20261120-004555 |
| free check | 50/50 hybrid, EiG | 1 |  |  |  | 54.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_eig_20261120-004727 |
| free check | 50/50 hybrid, GOAt | 1 |  |  |  | 55.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_goat_20261120-004753 |
| free check | 50/50 hybrid with sources, EiG | 1 |  |  |  | 54.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_eig_src_20261120-012630 |
| free check | 50/50 hybrid with sources, GOAt | 1 |  |  |  | 55.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_goat_src_20261120-012559 |
| free check | 50/50 hybrid, 400-node subgraph | 1 |  |  |  | 54.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_eig_n400_20261120-012753 |
| free check | 50/50 hybrid, 800-node subgraph | 1 |  |  |  | 53.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_eig_n800_20261120-012810 |
| free check | 50/50 hybrid, 1,600-node subgraph | 1 |  |  |  | 54.0 | 0 | runs/run-01/exp_c_fake_mh_262k_hybrid_eig_n1600_20261120-012818 |
| free check | Top-5 hybrid, EiG | 1 |  |  |  | 51.0 | 0 | runs/run-01/exp_c_fake_mh_262k_topk5_eig_20261120-015309 |
| free check | Top-10 hybrid, EiG | 1 |  |  |  | 53.0 | 0 | runs/run-01/exp_c_fake_mh_262k_topk10_eig_20261120-015308 |
| free check | Question graph, EiG | 1 |  |  |  | 51.0 | 0 | runs/run-01/exp_c_fake_mh_262k_qgraph_eig_20261120-021530 |
| free check | Bigger subgraphs, 1,600-node GNN | 1 |  |  |  | 48.0 | 0 | runs/run-01/exp_c_fake_mh_262k_gnn1600_eig_20261120-022639 |
| free check | Embedding search only (no graph) | 1 |  |  |  | 29.0 | 0 | runs/run-01/exp_embed_fake_mh_262k_20261120-012723 |
