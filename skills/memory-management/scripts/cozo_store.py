from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pycozo.client import Client

try:
    from .models import ContextPackage, Decision, Edge, Interface, Node, ScoredNode
    from .store import NodeNotFound, StoreError
except ImportError:
    from models import ContextPackage, Decision, Edge, Interface, Node, ScoredNode
    from store import NodeNotFound, StoreError

SCHEMA_RELATIONS = [
    """:create node {
        id: String,
        project: String,
        =>
        name: String,
        node_type: String,
        level: Int,
        description: String,
        status: String,
        origin: String,
        tokens_estimate: Int default 0,
        created_at: String,
        updated_at: String,
        embedding: <F32; 384>?
    }""",
    """:create edge_hierarchy {
        parent_id: String,
        child_id: String,
        order_idx: Int default 0
    }""",
    """:create edge_dependency {
        from_id: String,
        to_id: String,
        dep_type: String default 'requires'
    }""",
    """:create decision {
        id: String,
        node_id: String,
        question: String,
        options: String,
        chosen: String,
        reasoning: String,
        tradeoffs: String,
        created_at: String
    }""",
    """:create interface_def {
        id: String,
        node_id: String,
        name: String,
        description: String,
        spec: String,
        created_at: String
    }""",
    """:create config {
        key: String,
        value: String
    }""",
]

HNSW_INDEX = """::hnsw create node:embedding_idx {
    dim: 384,
    m: 16,
    ef_construction: 200,
    fields: [embedding],
    distance: Cosine,
    filter: status != 'failed'
}"""


class CozoStore:
    def __init__(self, db_path: str, embedding_provider=None):
        self.db_path = db_path
        self.embedding_provider = embedding_provider
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.client = Client("sqlite", db_path, dataframe=False)
        self._schema_ready = False

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return

        existing = {row[0] for row in self.client.run("::relations")["rows"]}
        for stmt in SCHEMA_RELATIONS:
            relation_name = stmt.split("{", 1)[0].split()[-1]
            if relation_name not in existing:
                self.client.run(stmt)

        try:
            self.client.run(HNSW_INDEX)
        except Exception:
            pass

        self._schema_ready = True

    def create_node(self, node: Node) -> None:
        self.ensure_schema()

        existing = self.client.run(
            "?[id] := *node{id, project}, project = $p, id = $i",
            {"p": node.project, "i": node.id},
        )
        if existing["rows"]:
            raise StoreError(f"node already exists: {node.id}")

        params = node.to_dict()
        embedding = self._embed_text(f"{node.name} {node.description}")
        if embedding is None:
            params["embedding"] = None
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at, embedding] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at, $embedding
                ]]
                :put node {
                    id, project => name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at, embedding
                }
                """,
                params,
            )
        else:
            params["embedding"] = embedding
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at, embedding] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at, vec($embedding)
                ]]
                :put node {
                    id, project => name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at, embedding
                }
                """,
                params,
            )

    def get_node(self, project: str, node_id: str) -> Node:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at] :=
              *node{id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at},
              project = $p, id = $i
            """,
            {"p": project, "i": node_id},
        )

        if not result["rows"]:
            raise NodeNotFound(node_id)

        cols = result["headers"]
        return Node(**dict(zip(cols, result["rows"][0])))

    def update_node(self, project: str, node_id: str, **fields) -> Node:
        self.ensure_schema()
        existing = self.get_node(project, node_id)
        updated = existing.to_dict()
        updated.update(fields)

        embedding = self._embed_text(f"{updated['name']} {updated['description']}")
        if embedding is None:
            updated["embedding"] = None
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at, embedding] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at, $embedding
                ]]
                :put node {
                    id, project => name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at, embedding
                }
                """,
                updated,
            )
        else:
            updated["embedding"] = embedding
            self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at, embedding] <- [[
                    $id, $project, $name, $node_type, $level, $description, $status, $origin,
                    $tokens_estimate, $created_at, $updated_at, vec($embedding)
                ]]
                :put node {
                    id, project => name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at, embedding
                }
                """,
                updated,
            )
        return Node(**{k: updated[k] for k in Node.__dataclass_fields__})

    def delete_node(self, project: str, node_id: str) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, project] <- [[$i, $p]]
            :rm node {id, project}
            """,
            {"i": node_id, "p": project},
        )

    def list_nodes(self, project: str, *, status: str | None = None) -> list[Node]:
        self.ensure_schema()
        if status is None:
            result = self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at] :=
                  *node{id, project, name, node_type, level, description, status, origin,
                        tokens_estimate, created_at, updated_at},
                  project = $p
                """,
                {"p": project},
            )
        else:
            result = self.client.run(
                """
                ?[id, project, name, node_type, level, description, status, origin,
                  tokens_estimate, created_at, updated_at] :=
                  *node{id, project, name, node_type, level, description, status, origin,
                        tokens_estimate, created_at, updated_at},
                  project = $p, status = $s
                """,
                {"p": project, "s": status},
            )

        cols = result["headers"]
        return [Node(**dict(zip(cols, row))) for row in result["rows"]]

    def add_edge(self, edge: Edge) -> None:
        self.ensure_schema()
        if edge.kind == "hierarchy":
            self.client.run(
                """
                ?[parent_id, child_id, order_idx] <- [[$f, $t, $o]]
                :put edge_hierarchy {parent_id, child_id => order_idx}
                """,
                {"f": edge.from_id, "t": edge.to_id, "o": edge.order_idx},
            )
        elif edge.kind == "dependency":
            self.client.run(
                """
                ?[from_id, to_id, dep_type] <- [[$f, $t, $d]]
                :put edge_dependency {from_id, to_id => dep_type}
                """,
                {"f": edge.from_id, "t": edge.to_id, "d": edge.dep_type},
            )
        else:
            raise StoreError(f"unknown edge kind: {edge.kind}")

    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None:
        self.ensure_schema()
        if kind == "hierarchy":
            self.client.run(
                """
                ?[parent_id, child_id] <- [[$f, $t]]
                :rm edge_hierarchy {parent_id, child_id}
                """,
                {"f": from_id, "t": to_id},
            )
        elif kind == "dependency":
            self.client.run(
                """
                ?[from_id, to_id] <- [[$f, $t]]
                :rm edge_dependency {from_id, to_id}
                """,
                {"f": from_id, "t": to_id},
            )

    def query_children(self, project: str, node_id: str) -> list[Node]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, project, name, node_type, level, description, status, origin,
              tokens_estimate, created_at, updated_at, order_idx] :=
              *edge_hierarchy{parent_id: $p, child_id: id, order_idx},
              *node{id, project, name, node_type, level, description, status, origin,
                    tokens_estimate, created_at, updated_at},
              project = $proj
            :order order_idx
            """,
            {"p": node_id, "proj": project},
        )
        cols = result["headers"]
        return [
            Node(**{k: dict(zip(cols, row))[k] for k in Node.__dataclass_fields__})
            for row in result["rows"]
        ]

    def query_ancestors(self, project: str, node_id: str) -> list[Node]:
        chain: list[Node] = []
        current = node_id
        seen = set()
        while True:
            if current in seen:
                break
            seen.add(current)
            result = self.client.run(
                "?[parent_id] := *edge_hierarchy{parent_id, child_id: $c}",
                {"c": current},
            )
            if not result["rows"]:
                break
            current = result["rows"][0][0]
            chain.append(self.get_node(project, current))
        return chain

    def query_subtree(self, project: str, root_id: str) -> list[Node]:
        out = [self.get_node(project, root_id)]
        for child in self.query_children(project, root_id):
            out.extend(self.query_subtree(project, child.id))
        return out

    def query_deps(self, project: str, node_id: str) -> list[Node]:
        self.ensure_schema()
        result = self.client.run(
            "?[to_id] := *edge_dependency{from_id: $f, to_id}",
            {"f": node_id},
        )
        return [self.get_node(project, row[0]) for row in result["rows"]]

    def detect_cycles(self, project: str) -> list[list[str]]:
        result = self.client.run("?[from_id, to_id] := *edge_dependency{from_id, to_id}")
        adj = defaultdict(list)
        for src, dst in result["rows"]:
            adj[src].append(dst)

        white, gray, black = 0, 1, 2
        color = defaultdict(lambda: white)
        cycles: list[list[str]] = []
        stack: list[str] = []

        def dfs(node_id: str) -> None:
            color[node_id] = gray
            stack.append(node_id)
            for nxt in adj[node_id]:
                if color[nxt] == gray:
                    idx = stack.index(nxt)
                    cycles.append(stack[idx:] + [nxt])
                elif color[nxt] == white:
                    dfs(nxt)
            stack.pop()
            color[node_id] = black

        for node_id in list(adj.keys()):
            if color[node_id] == white:
                dfs(node_id)
        return cycles

    def store_decision(self, decision: Decision) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, node_id, question, options, chosen, reasoning, tradeoffs, created_at] <- [[
                $id, $node_id, $question, $options, $chosen, $reasoning, $tradeoffs, $created_at
            ]]
            :put decision {id, node_id => question, options, chosen, reasoning, tradeoffs, created_at}
            """,
            decision.to_dict(),
        )

    def list_decisions(self, project: str, node_id: str) -> list[Decision]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, node_id, question, options, chosen, reasoning, tradeoffs, created_at] :=
              *decision{id, node_id, question, options, chosen, reasoning, tradeoffs, created_at},
              node_id = $n
            """,
            {"n": node_id},
        )
        cols = result["headers"]
        return [Decision(**dict(zip(cols, row))) for row in result["rows"]]

    def add_interface(self, iface: Interface) -> None:
        self.ensure_schema()
        self.client.run(
            """
            ?[id, node_id, name, description, spec, created_at] <- [[
                $id, $node_id, $name, $description, $spec, $created_at
            ]]
            :put interface_def {id, node_id => name, description, spec, created_at}
            """,
            iface.to_dict(),
        )

    def list_interfaces(self, project: str, node_id: str) -> list[Interface]:
        self.ensure_schema()
        result = self.client.run(
            """
            ?[id, node_id, name, description, spec, created_at] :=
              *interface_def{id, node_id, name, description, spec, created_at},
              node_id = $n
            """,
            {"n": node_id},
        )
        cols = result["headers"]
        return [Interface(**dict(zip(cols, row))) for row in result["rows"]]

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        import re

        if semantic and self.embedding_provider and self.embedding_provider.name != "skip":
            try:
                qvec = self.embedding_provider.embed([query])[0]
                if qvec is not None:
                    result = self.client.run(
                        """
                        ?[dist, id, project, name, node_type, level, description, status, origin,
                          tokens_estimate, created_at, updated_at] :=
                          ~node:embedding_idx{
                            id, project, name, node_type, level, description, status, origin,
                            tokens_estimate, created_at, updated_at |
                            query: vec($q),
                            k: $k,
                            ef: 50,
                            bind_distance: dist
                          },
                          project = $p
                        :order +dist
                        """,
                        {"q": qvec, "k": k, "p": project},
                    )

                    cols = result["headers"]
                    out: list[ScoredNode] = []
                    for row in result["rows"]:
                        row_map = dict(zip(cols, row))
                        node_fields = {f: row_map[f] for f in Node.__dataclass_fields__}
                        out.append(
                            ScoredNode(
                                node=Node(**node_fields),
                                score=1.0 - float(row_map["dist"]),
                                match_type="semantic",
                            )
                        )
                    if out:
                        return out
            except Exception:
                pass

        terms = [t.lower() for t in re.findall(r"\w+", query)]
        nodes = self.list_nodes(project)
        scored: list[ScoredNode] = []
        for node in nodes:
            text = (node.name + " " + node.description).lower()
            score = sum(text.count(t) for t in terms)
            if score > 0:
                scored.append(ScoredNode(node=node, score=float(score), match_type="bm25"))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:k]

    def _embed_text(self, text: str):
        if not self.embedding_provider or self.embedding_provider.name == "skip":
            return None
        try:
            vector = self.embedding_provider.embed([text])[0]
            if vector is None:
                return None
            return [float(x) for x in vector]
        except Exception:
            return None

    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage:
        leaf = self.get_node(project, leaf_id)
        ancestors_nodes = self.query_ancestors(project, leaf_id)
        ancestors = [a.to_dict() for a in ancestors_nodes]

        decisions = [d.to_dict() for d in self.list_decisions(project, leaf_id)]
        for ancestor in ancestors_nodes:
            decisions.extend(d.to_dict() for d in self.list_decisions(project, ancestor.id))

        interfaces = [i.to_dict() for i in self.list_interfaces(project, leaf_id)]
        deps_nodes = self.query_deps(project, leaf_id)
        for dep_node in deps_nodes:
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
            deps=[d.to_dict() for d in deps_nodes],
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
