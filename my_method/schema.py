"""Load the graph schema (schema.yaml) and check extracted facts against it."""

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_SCHEMA = Path(__file__).resolve().parent / "schema.yaml"


@dataclass
class Schema:
    name: str
    description: str
    node_types: dict
    edge_types: dict
    revision_key: list[str]
    relations: list[str] | None

    @classmethod
    def load(cls, path: str | Path = DEFAULT_SCHEMA) -> "Schema":
        raw = yaml.safe_load(Path(path).read_text())
        return cls(raw["name"], raw["description"], raw["node_types"], raw["edge_types"],
                   raw["revision_key"], raw.get("relations"))

    @property
    def fact_fields(self) -> list[str]:
        return list(self.node_types["Fact"]["fields"])

    def validate_fact(self, fact: dict) -> str | None:
        """Return why a fact does not fit the schema, or None if it fits."""
        for name in self.fact_fields:
            if not isinstance(fact.get(name), str) or not fact[name].strip():
                return f"missing field '{name}'"
        if self.relations is not None and fact["relation"].strip().lower() not in self.relations:
            return f"relation '{fact['relation']}' is not in the schema's relation list"
        return None

    def describe(self) -> str:
        """The schema as text for the writer's extraction prompt."""
        lines = [f"Schema '{self.name}': {self.description}", "", "Node types:"]
        for node, spec in self.node_types.items():
            lines.append(f"- {node}: {spec['description']}")
            lines += [f"    {field}: {meaning}" for field, meaning in spec["fields"].items()]
        lines.append("Edge types:")
        lines += [f"- {edge}: {spec['from']} -> {spec['to']}, {spec['description']}"
                  for edge, spec in self.edge_types.items()]
        if self.relations is not None:
            lines.append("Allowed relation labels: " + ", ".join(self.relations))
        return "\n".join(lines)
