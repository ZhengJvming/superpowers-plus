from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Node:
    id: str
    project: str
    name: str
    node_type: str
    level: int
    description: str
    status: str
    origin: str
    tokens_estimate: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Node":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


@dataclass
class Edge:
    kind: str
    from_id: str
    to_id: str
    order_idx: int = 0
    dep_type: str = "requires"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    id: str
    node_id: str
    question: str
    options: str
    chosen: str
    reasoning: str
    tradeoffs: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Interface:
    id: str
    node_id: str
    name: str
    description: str
    spec: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredNode:
    node: Node
    score: float
    match_type: str


@dataclass
class ContextPackage:
    node: dict[str, Any]
    ancestors: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    interfaces: list[dict[str, Any]]
    deps: list[dict[str, Any]]
    tokens_estimate: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
