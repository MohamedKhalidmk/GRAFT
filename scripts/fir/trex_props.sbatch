#!/bin/bash
#SBATCH --account=def-sylu_cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --job-name=trex-props
#SBATCH --output=%x-%j.out
# Test 06: T-REx property frequencies (all properties), for the guide's extended relation list. Free.
set -euo pipefail
source "$SLURM_SUBMIT_DIR/scripts/fir/common.sh"
.venv/bin/python - <<'EOF'
import glob, json, os, collections
import pyarrow.parquet as pq
c = collections.Counter()
for f in sorted(glob.glob(os.path.expanduser("~/scratch/sgar/trex/*.parquet"))):
    c.update(pq.read_table(f, columns=["relation"]).column("relation").to_pylist())
out = os.path.expanduser("~/scratch/sgar/trex/property_counts.json")
json.dump(c.most_common(), open(out, "w"))
print(len(c), "properties;", sum(c.values()), "triples; top:", c.most_common(10))
EOF
