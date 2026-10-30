"""Turn (graph, question, answer) examples into PyG graphs with features and weak labels."""

from dataclasses import dataclass

import torch
from torch_geometric.data import Data

from my_method.gnn.data_synthetic import Example
from my_method.gnn.features import N_STRUCTURAL, TextEmbedder, build_features, node_text, select_subgraph
from my_method.gnn.labels import weak_labels


@dataclass
class SubgraphConfig:
    max_nodes: int = 400  # chosen by select_subgraph; bounds GOAt's cost, which grows with nodes x edges


def to_pyg(example: Example, texts: TextEmbedder, cfg: SubgraphConfig) -> Data | None:
    """None when the answer falls outside the subgraph or no node is on a question-answer path."""
    nodes = select_subgraph(example.store, example.question_entities, cfg.max_nodes)
    if not any(a in nodes for a in example.answer_entities):
        return None
    labels = weak_labels(example.store, nodes, example.question_entities, example.answer_entities)
    if not any(labels):
        return None
    t = build_features(example.store, nodes, example.question_entities, example.question, texts)
    answer_mask = torch.tensor([n in example.answer_entities for n in nodes])
    # keep only the structural features per graph: text vectors live once in texts.table()
    text_ids = torch.tensor(texts.ids([node_text(example.store, n) for n in nodes]))
    return Data(x=t.x[:, :N_STRUCTURAL].clone(), text_ids=text_ids, edge_index=t.edge_index,
                y=torch.tensor(labels), answer_mask=answer_mask)


def build_dataset(groups: list[list[Example]], texts: TextEmbedder, cfg: SubgraphConfig) -> list[list[Data]]:
    return [[d for d in (to_pyg(e, texts, cfg) for e in group) if d is not None] for group in groups]
