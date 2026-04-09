"""Pure-Python tree renderers."""

from __future__ import annotations

from typing import Optional

try:
    from .models import Node
except ImportError:
    from models import Node


_STATUS_ICON = {
    "done": " ✓",
    "leaf": " ✓",
    "in_progress": " …",
    "draft": "",
}

_MERMAID_CLASSES = {
    "leaf": "fill:#d4edda,stroke:#28a745",
    "branch": "fill:#cce5ff,stroke:#0d6efd",
    "root": "fill:#e2e3e5,stroke:#6c757d",
    "draft": "fill:#f8f9fa,stroke:#adb5bd",
    "existing_module": "fill:#fff3cd,stroke:#ffc107",
    "change_root": "fill:#ffe0cc,stroke:#fd7e14",
    "change_branch": "fill:#ffe0cc,stroke:#fd7e14",
    "change_leaf": "fill:#ffe0cc,stroke:#fd7e14",
}


def render_ascii(root_id: str, nodes: dict[str, Node], children: dict[str, list[str]]) -> str:
    lines: list[str] = []

    def _walk(node_id: str, prefix: str, is_last: bool, is_root: bool) -> None:
        node = nodes[node_id]
        icon = _STATUS_ICON.get(node.status, "")
        label = f"{node.name} [{node.node_type}, {node.status}]{icon}"

        if is_root:
            lines.append(label)
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{label}")

        child_ids = children.get(node_id, [])
        next_prefix = prefix + ("    " if is_last else "│   ")
        for idx, child_id in enumerate(child_ids):
            _walk(child_id, next_prefix if not is_root else "", idx == len(child_ids) - 1, False)

    _walk(root_id, "", True, True)
    return "\n".join(lines)


def render_mermaid(
    root_id: str,
    nodes: dict[str, Node],
    children: dict[str, list[str]],
    dep_edges: Optional[list[tuple[str, str]]] = None,
) -> str:
    lines = ["graph TD"]

    for node_id, node in nodes.items():
        label = f'{node.name}<br/><small>{node.node_type} · {node.status}</small>'
        lines.append(f'  {node_id}["{label}"]')

    for parent_id, child_ids in children.items():
        for child_id in child_ids:
            lines.append(f"  {parent_id} --> {child_id}")

    if dep_edges:
        for from_id, to_id in dep_edges:
            lines.append(f"  {from_id} -.->|depends| {to_id}")

    lines.append("")
    for class_name, style in _MERMAID_CLASSES.items():
        lines.append(f"  classDef {class_name} {style}")

    for node_id, node in nodes.items():
        class_name = node.node_type if node.node_type in _MERMAID_CLASSES else "draft"
        if node.status == "draft" and node.node_type not in {"existing_module"}:
            class_name = "draft"
        lines.append(f"  class {node_id} {class_name}")

    return "\n".join(lines)
