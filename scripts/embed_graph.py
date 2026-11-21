"""Embed every node of a GRAFT graph once and save the vectors next to it, so later passes load them instead of
re-embedding (1.58M nodes: minutes on a GPU, over an hour on 8 CPUs). Self-contained: needs only numpy and
sentence-transformers, so it runs on any cluster with the graph file copied over.

    python scripts/embed_graph.py GRAPH.json [--model BAAI/bge-small-en-v1.5] [--batch 512]
Writes GRAPH.json.emb.npy (float32, one row per text, normalised as GRAFT's embedder does) and
GRAPH.json.emb.texts.json (the texts, in row order). Node text = entity name, or "subject relation object" for a fact
(my_method/gnn/features.node_text)."""
import argparse, json, time
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("graph"); ap.add_argument("--model", default="BAAI/bge-small-en-v1.5"); ap.add_argument("--batch", type=int, default=512)
ap.add_argument("--device", default=None, help="cpu | cuda (default: sentence-transformers picks; never Apple MPS, which gives wrong vectors)")
a = ap.parse_args()
t0 = time.time()
data = json.loads(Path(a.graph).read_text())
texts = list(dict.fromkeys(n["name"] if n["type"] == "Entity" else f"{n['subject']} {n['relation']} {n['object']}"
                           for n in data["nodes"] if n.get("type") in ("Entity", "Fact")))
del data
print(f"{len(texts):,} texts, loaded in {time.time() - t0:.0f} s", flush=True)
from sentence_transformers import SentenceTransformer
import sys
m = SentenceTransformer(a.model, trust_remote_code=True, device=a.device or ("cpu" if sys.platform == "darwin" else None))
print("device", m.device, flush=True)
t1 = time.time()
vecs = m.encode(texts, batch_size=a.batch, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
assert np.isfinite(vecs).all()
print(f"embedded in {time.time() - t1:.0f} s", flush=True)
import os
out, tag = Path(a.graph + ".emb.npy"), f".{os.uname().nodename}.{os.getpid()}.part"
np.save(str(out) + tag + ".npy", vecs)  # twins on other nodes write their own part files
Path(a.graph + ".emb.texts.json" + tag).write_text(json.dumps(texts, ensure_ascii=False))
Path(a.graph + ".emb.texts.json" + tag).rename(a.graph + ".emb.texts.json")
Path(str(out) + tag + ".npy").rename(out)  # the .npy appears only when complete
print("wrote", out, vecs.shape, flush=True)
