from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional, Protocol

from .models import ContextPackage, Decision, Edge, Interface, Node, ScoredNode


class StoreError(Exception):
    pass


class NodeNotFound(StoreError):
    pass


class MemoryStore(Protocol):
    """Storage backend contract."""

    def create_node(self, node: Node) -> None: ...
    def get_node(self, project: str, node_id: str) -> Node: ...
    def update_node(self, project: str, node_id: str, **fields) -> Node: ...
    def delete_node(self, project: str, node_id: str) -> None: ...
    def list_nodes(self, project: str, *, status: Optional[str] = None) -> list[Node]: ...

    def add_edge(self, edge: Edge) -> None: ...
    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None: ...

    def query_children(self, project: str, node_id: str) -> list[Node]: ...
    def query_ancestors(self, project: str, node_id: str) -> list[Node]: ...
    def query_subtree(self, project: str, root_id: str) -> list[Node]: ...
    def query_deps(self, project: str, node_id: str) -> list[Node]: ...
    def detect_cycles(self, project: str) -> list[list[str]]: ...

    def store_decision(self, decision: Decision) -> None: ...
    def list_decisions(self, project: str, node_id: str) -> list[Decision]: ...
    def add_interface(self, iface: Interface) -> None: ...
    def list_interfaces(self, project: str, node_id: str) -> list[Interface]: ...

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]: ...
    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage: ...

    def validate(self, project: str) -> dict: ...
    def stats(self, project: str) -> dict: ...


class InMemoryStore:
    """Reference impl for tests. Pure Python, no external dependencies."""

    def __init__(self):
        self._nodes: dict[tuple[str, str], Node] = {}
        self._edges: list[Edge] = []
        self._decisions: list[Decision] = []
        self._interfaces: list[Interface] = []

    def create_node(self, node: Node) -> None:
        key = (node.project, node.id)
        if key in self._nodes:
            raise StoreError(f"node already exists: {node.id}")
        self._nodes[key] = node

    def get_node(self, project: str, node_id: str) -> Node:
        try:
            return self._nodes[(project, node_id)]
        except KeyError as exc:
            raise NodeNotFound(node_id) from exc

    def update_node(self, project: str, node_id: str, **fields) -> Node:
        node = self.get_node(project, node_id)
        for key, value in fields.items():
            setattr(node, key, value)
        return node

    def delete_node(self, project: str, node_id: str) -> None:
        self._nodes.pop((project, node_id), None)
        self._edges = [e for e in self._edges if e.from_id != node_id and e.to_id != node_id]

    def list_nodes(self, project: str, *, status: Optional[str] = None) -> list[Node]:
        nodes = [n for (p, _), n in self._nodes.items() if p == project]
        if status is not None:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None:
        self._edges = [
            e
            for e in self._edges
            if not (e.kind == kind and e.from_id == from_id and e.to_id == to_id)
        ]

    def query_children(self, project: str, node_id: str) -> list[Node]:
        edges = sorted(
            [e for e in self._edges if e.kind == "hierarchy" and e.from_id == node_id],
            key=lambda e: e.order_idx,
        )
        return [self.get_node(project, edge.to_id) for edge in edges]

    def query_ancestors(self, project: str, node_id: str) -> list[Node]:
        chain: list[Node] = []
        current = node_id
        while True:
            parent_edges = [e for e in self._edges if e.kind == "hierarchy" and e.to_id == current]
            if not parent_edges:
                break
            current = parent_edges[0].from_id
            chain.append(self.get_node(project, current))
        return chain

    def query_subtree(self, project: str, root_id: str) -> list[Node]:
        out = [self.get_node(project, root_id)]
        for child in self.query_children(project, root_id):
            out.extend(self.query_subtree(project, child.id))
        return out

    def query_deps(self, project: str, node_id: str) -> list[Node]:
        deps = [e.to_id for e in self._edges if e.kind == "dependency" and e.from_id == node_id]
        return [self.get_node(project, dep_id) for dep_id in deps]

    def detect_cycles(self, project: str) -> list[list[str]]:
        adj = defaultdict(list)
        for edge in self._edges:
            if edge.kind == "dependency":
                adj[edge.from_id].append(edge.to_id)

        white, gray, black = 0, 1, 2
        color = defaultdict(lambda: white)
        cycles: list[list[str]] = []
        stack: list[str] = []

        def dfs(node_id: str) -> None:
            color[node_id] = gray
            stack.append(node_id)
            for dep in adj[node_id]:
                if color[dep] == gray:
                    idx = stack.index(dep)
                    cycles.append(stack[idx:] + [dep])
                elif color[dep] == white:
                    dfs(dep)
            stack.pop()
            color[node_id] = black

        for key in list(adj.keys()):
            if color[key] == white:
                dfs(key)

        return cycles

    def store_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)

    def list_decisions(self, project: str, node_id: str) -> list[Decision]:
        node_ids = {n.id for n in self.list_nodes(project)}
        return [d for d in self._decisions if d.node_id == node_id and node_id in node_ids]

    def add_interface(self, iface: Interface) -> None:
        self._interfaces.append(iface)

    def list_interfaces(self, project: str, node_id: str) -> list[Interface]:
        return [i for i in self._interfaces if i.node_id == node_id]

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        terms = [t.lower() for t in re.findall(r"\w+", query)]
        scored: list[ScoredNode] = []
        for node in self.list_nodes(project):
            text = (node.name + " " + node.description).lower()
            score = sum(text.count(term) for term in terms)
            if score > 0:
                scored.append(ScoredNode(node=node, score=float(score), match_type="bm25"))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]

    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage:
        leaf = self.get_node(project, leaf_id)
        ancestors = [a.to_dict() for a in self.query_ancestors(project, leaf_id)]
        deps = [d.to_dict() for d in self.query_deps(project, leaf_id)]

        decisions = [d.to_dict() for d in self.list_decisions(project, leaf_id)]
        for ancestor in self.query_ancestors(project, leaf_id):
            decisions.extend(d.to_dict() for d in self.list_decisions(project, ancestor.id))

        interfaces = [i.to_dict() for i in self.list_interfaces(project, leaf_id)]
        for dep_node in self.query_deps(project, leaf_id):
            interfaces.extend(i.to_dict() for i in self.list_interfaces(project, dep_node.id))

        total_chars = (
            len(leaf.description)
            + sum(len(a["description"]) for a in ancestors)
            + sum(len(d["reasoning"]) + len(d["tradeoffs"]) for d in decisions)
            + sum(len(i["spec"]) for i in interfaces)
        )

        return ContextPackage(
            node=leaf.to_dict(),
            ancestors=ancestors,
            decisions=decisions,
            interfaces=interfaces,
            deps=deps,
            tokens_estimate=total_chars // 4,
        )

    def validate(self, project: str) -> dict:
        violations: list[dict] = []
        for node in self.list_nodes(project):
            if node.node_type == "branch" and not self.list_decisions(project, node.id):
                violations.append({"node_id": node.id, "rule": "branch_requires_decision"})
            if node.node_type == "leaf" and not self.list_interfaces(project, node.id):
                violations.append({"node_id": node.id, "rule": "leaf_requires_interface"})
        return {"passed": len(violations) == 0, "violations": violations}

    def stats(self, project: str) -> dict:
        nodes = self.list_nodes(project)
        total = len(nodes)
        inferred = sum(1 for n in nodes if n.origin == "skill_inferred")
        ratio = (inferred / total) if total else 0.0
        return {
            "total_nodes": total,
            "skill_inferred_nodes": inferred,
            "user_stated_nodes": total - inferred,
            "skill_inferred_node_ratio": round(ratio, 4),
        }
