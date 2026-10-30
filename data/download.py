"""Prefetch the MemoryAgentBench FactConsolidation data into the Hugging Face cache.

Run on a machine with internet (e.g. a Fir login node) before running jobs on nodes that may
have none. Set HF_HOME first; on Fir, point it at ~/scratch.

    python -m data.download
"""

from datasets import load_dataset

if __name__ == "__main__":
    data = load_dataset("ai-hyz/MemoryAgentBench", split="Conflict_Resolution", revision="main")
    print(f"cached {len(data)} FactConsolidation contexts:",
          sorted(row["metadata"]["source"] for row in data))
