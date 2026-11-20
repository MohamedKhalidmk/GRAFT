"""The GRAFT memory graph: Entity and Fact nodes, subject_of / object_of / SUPERSEDES edges.

Stored as a NetworkX MultiDiGraph and saved as node-link JSON, so it is easy to inspect.
Superseded facts are never deleted: a SUPERSEDES edge points from the newer fact to the older.
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import networkx as nx


@dataclass
class Provenance:
    chunk_id: int  # index of the chunk the fact was read from
    arrival: int  # global order in which the writer stored facts (0 = first)
    serial: int | None  # the fact's serial number in the text, if it has one
    span: str  # the raw text the fact was extracted from


def norm(text: str) -> str:
    """Key used to match entity names and relations: lowercase, no edge punctuation, single spaces."""
    return re.sub(r"\s+", " ", text.strip().strip(".,;:!?\"'").lower())


def entity_id(name: str) -> str:
    return "e:" + norm(name)


# NLTK's English stopword list (articles, pronouns, question words, auxiliaries, prepositions, conjunctions)
STOPWORDS = frozenset("""i me my myself we our ours ourselves you your yours yourself yourselves he him his himself she her
hers herself it its itself they them their theirs themselves what which who whom whose this that these those am is are
was were be been being have has had having do does did doing a an the and but if or because as until while of at by for
with about against between into through during before after above below to from up down in out on off over under again
further then once here there when where why how all any both each few more most other some such no nor not only own same
so than too very s t can will just don should now d ll m o re ve y ain""".split())


def is_stopword_name(name: str) -> bool:
    """True for a name that is a single stopword, article or question word ("The", "who", "A."). Never linked:
    in a question it is not a mention of anything, and it would match every question. Multi-word names that are
    all stopwords ("The Who", "Take That") are real names and stay."""
    words = re.findall(r"[a-z0-9]+", str(name).lower())
    return len(words) == 1 and words[0] in STOPWORDS


class GraphStore:
    def __init__(self):
        self.g = nx.MultiDiGraph()
        self.next_fact = 0
        self.next_arrival = 0
        self._simple: nx.Graph | None = None

    # ---- writing ----

    def add_entity(self, name: str) -> str:
        self._simple = None
        node = entity_id(name)
        if node not in self.g:
            self.g.add_node(node, type="Entity", name=name.strip())
        return node

    def add_fact(self, subject: str, relation: str, obj: str, prov: Provenance, **attrs) -> str:
        self._simple = None
        node = f"f:{self.next_fact}"
        self.next_fact += 1
        s, o = self.add_entity(subject), self.add_entity(obj)
        self.g.add_node(node, type="Fact", subject=subject.strip(), relation=norm(relation), object=obj.strip(),
                        provenance=asdict(prov), mentions=[asdict(prov)], **attrs)
        self.g.add_edge(s, node, type="subject_of")
        self.g.add_edge(o, node, type="object_of")
        return node

    def merge(self, fact: str, prov: Provenance) -> None:
        """Record another mention of an existing fact."""
        self.g.nodes[fact]["mentions"].append(asdict(prov))

    def supersede(self, newer: str, older: str) -> None:
        self._simple = None
        self.g.add_edge(newer, older, type="SUPERSEDES")

    def take_arrival(self) -> int:
        arrival = self.next_arrival
        self.next_arrival += 1
        return arrival

    # ---- reading ----

    def fact(self, node: str) -> dict:
        return self.g.nodes[node]

    def simple_graph(self) -> nx.Graph:
        """Undirected view with one edge per node pair, for graph walks; cached until the next write."""
        if self._simple is None:
            self._simple = nx.Graph(self.g)
        return self._simple

    def facts(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d["type"] == "Fact"]

    def entities(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d["type"] == "Entity"]

    def superseded_by(self, fact: str) -> list[str]:
        return [u for u, _, d in self.g.in_edges(fact, data=True) if d["type"] == "SUPERSEDES"]

    def is_superseded(self, fact: str) -> bool:
        return bool(self.superseded_by(fact))

    def current(self, fact: str) -> str:
        """Follow SUPERSEDES edges to the newest version (latest arrival wins on branches)."""
        seen = {fact}
        while newer := [n for n in self.superseded_by(fact) if n not in seen]:
            fact = max(newer, key=lambda n: self.fact(n)["provenance"]["arrival"])
            seen.add(fact)
        return fact

    def facts_of_entity(self, entity: str, role: str | None = None) -> list[str]:
        """Facts the entity takes part in; role 'subject_of' / 'object_of' restricts it."""
        return [v for _, v, d in self.g.out_edges(entity, data=True)
                if d["type"] in ("subject_of", "object_of") and (role is None or d["type"] == role)]

    def facts_with_key(self, subject: str, relation: str) -> list[str]:
        """All versions (current and superseded) of the fact identified by (subject, relation)."""
        node = entity_id(subject)
        if node not in self.g:
            return []
        return [f for f in self.facts_of_entity(node, "subject_of") if self.fact(f)["relation"] == norm(relation)]

    def stats(self) -> dict:
        types = [d["type"] for _, _, d in self.g.edges(data=True)]
        return {"entities": len(self.entities()), "facts": len(self.facts()),
                "supersedes_edges": types.count("SUPERSEDES"),
                "current_facts": sum(not self.is_superseded(f) for f in self.facts())}

    # ---- persistence ----

    def save(self, path: str | Path) -> None:
        data = nx.node_link_data(self.g, edges="edges")
        data["counters"] = {"next_fact": self.next_fact, "next_arrival": self.next_arrival}
        Path(path).write_text(json.dumps(data, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> "GraphStore":
        data = json.loads(Path(path).read_text())
        store = cls()
        counters = data.pop("counters")
        store.g = nx.node_link_graph(data, directed=True, multigraph=True, edges="edges")
        store.next_fact, store.next_arrival = counters["next_fact"], counters["next_arrival"]
        return store
