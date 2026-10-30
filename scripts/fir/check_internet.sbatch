#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --time=00:05:00
#SBATCH --mem=1G
#SBATCH --job-name=sgar-net
#SBATCH --output=%x-%j.out
# Real runs call the Anthropic API from the compute node. This only checks reachability
# (an unauthenticated request; no key is sent, nothing is billed).
curl -s -o /dev/null -w "api.anthropic.com HTTP %{http_code}\n" --max-time 20 https://api.anthropic.com/v1/models \
  || echo "NO INTERNET from compute nodes: real runs must go through a proxy or run elsewhere"
