"""Everything the T-REx base cleaning dropped, for a person to read.

    python experiments/test-04-base-graph-trex-full/dropped_items.py
Reads runs/run-02/cleaning/: dropped_detail.json (scripts/fir/dropped_detail.py: each dropped entity with all its
facts, the generic words kept), clean_report.json (scripts/fir/clean_base.py, the rule used),
clean_report_v1_too_wide.json (the first, too-wide rule, never used) and wikidata_ids.json (Wikidata IDs: exact from
the entity's own Wikipedia article where a fact came from it, otherwise label-search candidates, not verified).
Writes dropped_items.md and dropped_items.html there; the PDF is printed from the HTML."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "runs" / "run-02" / "cleaning"


def qid_text(q: dict | None) -> str:
    if not q:
        return "not looked up"
    if q.get("qid"):
        return f"[{q['qid']}](https://www.wikidata.org/wiki/{q['qid']}) ({q.get('description') or 'no description'}; from {q['how']})"
    c = q.get("candidates") or []
    if not c:
        return "no Wikidata match by label"
    return "label search, not verified: " + ", ".join(f"[{i}](https://www.wikidata.org/wiki/{i}) ({d or 'no description'})" for i, d in c)


def main() -> None:
    det = json.loads((D / "dropped_detail.json").read_text())
    rep = json.loads((D / "clean_report.json").read_text())
    v1 = json.loads((D / "clean_report_v1_too_wide.json").read_text())
    q = json.loads((D / "wikidata_ids.json").read_text())
    b, s = rep["base"], rep["shared"]
    md = ["# T-REx base cleaning: everything dropped", "",
          "Test 04 run-02. The rule (scripts/fir/clean_base.py): a base entity is dropped when its whole name is one "
          "stopword (not all-caps, not a contraction fragment like Ain or Don), one number, or punctuation, unless a "
          "document fact uses it; its base facts go with it. Generic lower-case words are reported, never dropped. "
          "Wikidata IDs: the T-REx export we use stores names only, so each ID is either exact (from the entity's own "
          "Wikipedia article, where one of its facts came from it) or a label-search candidate marked not verified.", "",
          "## Summary", "",
          "| | Base (T-REx) | Built graph (base + documents) |", "|---|---|---|",
          f"| Entities dropped | {b['junk_entities_removed']} | {s['junk_entities_removed']} |",
          f"| Facts dropped | {b['base_facts_removed']} | {s['base_facts_removed']} |",
          f"| Base entities left with no facts, dropped | {b['orphan_base_entities_removed']} | {s['orphan_base_entities_removed']} |",
          f"| Nodes | {b['nodes_before']:,} -> {b['nodes_after']:,} | {s['nodes_before']:,} -> {s['nodes_after']:,} |",
          f"| Edges | {b['edges_before']:,} -> {b['edges_after']:,} | {s['edges_before']:,} -> {s['edges_after']:,} |",
          f"| Facts | {b['facts_before']:,} -> {b['facts_after']:,} | {s['facts_before']:,} -> {s['facts_after']:,} |",
          f"| SUPERSEDES edges removed | {b['supersedes_edges_removed']} | {s['supersedes_edges_removed']} |", "",
          f"By category (base): {b['by_category']}. Kept because documents use them: "
          f"{', '.join(x[0] for x in s['kept_because_documents_use_them']) or 'none'} (in the built graph). "
          f"Document links that pointed to a dropped entity: {rep['document_links_to_junk']['count']} "
          f"({'; '.join(f'{a} -> {m}' for a, m, _ in rep['document_links_to_junk']['examples'])}). "
          f"Base entities left with no facts and dropped with them: {b['orphan_base_entities_removed']} (those named in "
          f"the facts below: {', '.join(det['orphans']) or 'none'}).", "",
          "## The dropped entities and their facts", ""]
    for e in sorted(det["dropped"], key=lambda x: (x["category"], x["name"])):
        md += [f"### {e['name']} ({e['category']}, {len(e['facts'])} fact{'s' * (len(e['facts']) != 1)})", "",
               f"Wikidata: {qid_text(q.get(e['name']))}", "", "| Subject | Relation | Object | Wikipedia article |", "|---|---|---|---|"]
        md += [f"| {f['subject']} | {f['relation']} | {f['object']} | {f['source_title']} |" for f in e["facts"]]
        md += [""]
    md += ["## Generic words reported but kept", "",
           "One-word names written in lower case in at least 1% of the base's Wikipedia sentences, or all-caps short "
           "names. Kept: on T-REx they are Wikidata concepts that are real answers (occupation, position, genre).", "",
           "| Name | Facts | Wikidata | Example fact |", "|---|---|---|---|"]
    for g in det["generic"]:
        ex = g["sample"][0] if g["sample"] else None
        md.append(f"| {g['name']} | {g['facts']:,} | {qid_text(q.get(g['name']))} | "
                  f"{(ex['subject'] + ' / ' + ex['relation'] + ' / ' + ex['object']) if ex else ''} |")
    vb = v1["base"]
    md += ["", "## The first, too-wide run (never used)", "",
           f"The first rule also dropped every generic word and every stopword-shaped name, all-caps included. It would "
           f"have removed {vb['junk_entities_removed']} entities and {vb['base_facts_removed']:,} base facts "
           f"({vb['facts_by_category']}), plus {vb['orphan_base_entities_removed']:,} orphaned entities: facts "
           f"{vb['facts_before']:,} -> {vb['facts_after']:,}. Almost all of it hung on real answers. It was caught "
           "before any run used it; its files are kept as *_clean_v1_too_wide*.", "",
           "| Name | Category | Facts |", "|---|---|---|"]
    md += [f"| {n} | {c} | {k:,} |" for n, c, k in vb["top_by_facts"]]
    (D / "dropped_items.md").write_text("\n".join(md) + "\n")
    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark", {"html": True}).enable("table").render("\n".join(md))
    css = """body{font:14px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:#1f2328;background:#fff;margin:0}
main{max-width:1050px;margin:28px auto;padding:0 22px} h2{border-bottom:2px solid #1f2328;padding-bottom:5px;margin-top:36px}
h3{font-size:15px;margin-top:22px;border-top:1px solid #d1d9e0;padding-top:12px} table{border-collapse:collapse;font-size:12.5px;margin:8px 0}
th,td{border:1px solid #d1d9e0;padding:4px 8px;text-align:left;vertical-align:top} th{background:#f6f8fa} a{color:#0969da}"""
    (D / "dropped_items.html").write_text(f"<!doctype html><meta charset=utf-8><title>T-REx cleaning: dropped</title>"
                                          f"<style>{css}</style><main>{body}</main>")
    print(len(det["dropped"]), "entities,", sum(len(x["facts"]) for x in det["dropped"]), "facts ->", D / "dropped_items.md")


if __name__ == "__main__":
    main()
