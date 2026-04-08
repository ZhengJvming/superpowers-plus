from __future__ import annotations

from pathlib import Path

from pycozo.client import Client

from .models import ContextPackage, Decision, Edge, Interface, Node, ScoredNode
from .store import NodeNotFound, StoreError

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
        embedding: <F32; 1024>?
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
    dim: 1024,
    m: 16,
    ef_construction: 200,
    fields: [embedding],
    distance: Cosine,
    filter: status != 'failed'
}"""


class CozoStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
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
        raise NotImplementedError

    def remove_edge(self, kind: str, from_id: str, to_id: str) -> None:
        raise NotImplementedError

    def query_children(self, project: str, node_id: str) -> list[Node]:
        raise NotImplementedError

    def query_ancestors(self, project: str, node_id: str) -> list[Node]:
        raise NotImplementedError

    def query_subtree(self, project: str, root_id: str) -> list[Node]:
        raise NotImplementedError

    def query_deps(self, project: str, node_id: str) -> list[Node]:
        raise NotImplementedError

    def detect_cycles(self, project: str) -> list[list[str]]:
        raise NotImplementedError

    def store_decision(self, decision: Decision) -> None:
        raise NotImplementedError

    def list_decisions(self, project: str, node_id: str) -> list[Decision]:
        raise NotImplementedError

    def add_interface(self, iface: Interface) -> None:
        raise NotImplementedError

    def list_interfaces(self, project: str, node_id: str) -> list[Interface]:
        raise NotImplementedError

    def recall(self, project: str, query: str, k: int, semantic: bool) -> list[ScoredNode]:
        raise NotImplementedError

    def assemble_context(self, project: str, leaf_id: str) -> ContextPackage:
        raise NotImplementedError

    def validate(self, project: str) -> dict:
        raise NotImplementedError

    def stats(self, project: str) -> dict:
        raise NotImplementedError
