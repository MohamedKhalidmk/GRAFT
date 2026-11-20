"""Does Qwen link entities as well as Haiku? Replays Haiku's logged linking decisions through Qwen, same prompt.

    python -m my_method.link_check --base results/checkpoints/base_graphs/trex_full_base.json \
        --log <shared graph>.partial.meta.json --chunks 12 --openai-base-url http://127.0.0.1:8000/v1 --model qwen_w4a16 \
        --out link_check.json
Takes Haiku's decisions for a seeded sample of chunks (all names of a chunk in one call, as the writer sent them),
rebuilds each prompt exactly (LINK_PROMPT, the same 10 candidates in the same order, one stored fact per candidate),
asks Qwen (thinking off, greedy), and counts: same base entity, both "new", disagreements (listed for review).
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from openai import OpenAI

from my_method.graph_store import GraphStore, entity_id
from my_method.writer import LINK_PROMPT, EntityLinker, parse_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--log", required=True, help="partial.meta.json (link_log) or <graph>.linking.jsonl")
    ap.add_argument("--chunks", type=int, default=12)
    ap.add_argument("--openai-base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    p = Path(a.log)
    log = json.loads(p.read_text())["link_log"] if p.suffix == ".json" else [json.loads(l) for l in open(p)]
    by_chunk = defaultdict(list)
    for d in log:
        by_chunk[d["chunk"]].append(d)
    chunks = sorted(random.Random(20261120).sample(sorted(by_chunk), min(a.chunks, len(by_chunk))))
    store = GraphStore.load(a.base)
    describe = EntityLinker._describe
    client = OpenAI(base_url=a.openai_base_url, api_key="EMPTY")
    rows = []
    for c in chunks:
        ds = by_chunk[c]
        lines = []
        for i, d in enumerate(ds):
            lines.append(f"N{i + 1}: {d['from']}")
            lines += [f"    c{k + 1}: {describe(None, store, entity_id(n))}" for k, n in enumerate(d["candidates"])]
        r = client.chat.completions.create(model=a.model, temperature=0.0, max_tokens=2048,
                                           messages=[{"role": "system", "content": LINK_PROMPT}, {"role": "user", "content": "\n".join(lines)}],
                                           extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        try:
            got = {str(x.get("name")): str(x.get("match", "new")) for x in parse_json(r.choices[0].message.content).get("links", [])}
        except (ValueError, json.JSONDecodeError):
            got = {}
        for i, d in enumerate(ds):
            q = got.get(f"N{i + 1}", "new")
            pick = lambda m: d["candidates"][int(m[1:]) - 1] if m.startswith("c") and m[1:].isdigit() and 1 <= int(m[1:]) <= len(d["candidates"]) else None
            h, qq = pick(d["choice"]), pick(q)
            rows.append({"chunk": c, "name": d["name"], "from": d["from"], "haiku": h, "qwen": qq,
                         "agree": h == qq, "kind": "both_new" if h is None and qq is None else "same_entity" if h == qq else "differ"})
    n = len(rows)
    out = {"chunks": chunks, "names": n, "agree": sum(r["agree"] for r in rows), "agree_share": round(sum(r["agree"] for r in rows) / n, 4),
           "same_entity": sum(r["kind"] == "same_entity" for r in rows), "both_new": sum(r["kind"] == "both_new" for r in rows),
           "haiku_matched": sum(r["haiku"] is not None for r in rows), "qwen_matched": sum(r["qwen"] is not None for r in rows),
           "disagreements": [r for r in rows if not r["agree"]]}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}))
    for r in out["disagreements"][:25]:
        print(f"  {r['name']!r}: Haiku={r['haiku']!r}  Qwen={r['qwen']!r}   [{r['from'][:90]}]")


if __name__ == "__main__":
    main()
