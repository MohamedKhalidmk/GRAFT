"""SubgraphRAG's training data: WebQSP and CWQ questions over Freebase subgraphs.

These are the RoG-preprocessed sets SubgraphRAG trains on (Hugging Face rmanluo/RoG-webqsp and
rmanluo/RoG-cwq): each question comes with its own subgraph (a list of [head, relation, tail]),
topic entities and answer entities. Each subgraph becomes a GraphStore with one Fact per triple.
There are no revisions in this data, so it teaches retrieval, not the latest-version preference.
Read with streaming, so only the requested number of examples is downloaded.
"""

from datasets import load_dataset

from my_method.graph_store import GraphStore, Provenance, entity_id
from my_method.gnn.data_synthetic import Example

DATASETS = {"webqsp": "rmanluo/RoG-webqsp", "cwq": "rmanluo/RoG-cwq"}


def to_store(triples: list[list[str]]) -> GraphStore:
    store = GraphStore()
    for i, (head, relation, tail) in enumerate(triples):
        store.add_fact(head, relation, tail, Provenance(chunk_id=0, arrival=i, serial=i,
                                                        span=f"{head} {relation} {tail}"))
        store.next_arrival = i + 1
    return store


def subgraphrag_examples(name: str, split: str, limit: int) -> list[list[Example]]:
    """One single-example group per question (each question has its own graph)."""
    rows = load_dataset(DATASETS[name], split=split, streaming=True)
    groups = []
    for row in rows:
        if len(groups) >= limit:
            break
        store = to_store([t for t in row["graph"] if len(t) == 3])
        q_entities = [entity_id(e) for e in row["q_entity"] if entity_id(e) in store.g]
        a_entities = [entity_id(e) for e in row["a_entity"] if entity_id(e) in store.g]
        if q_entities and a_entities:
            groups.append([Example(store, row["question"], q_entities, a_entities, hops=0)])
    return groups
