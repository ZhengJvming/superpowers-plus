#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pycozo[embedded]>=0.7",
#   "click>=8.1",
#   "tomli>=2.0; python_version<'3.11'",
# ]
# ///
"""Pyramid Memory CLI - Milestone 1 (storage + CLI)."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import click

from config import Config, default_config_path, default_db_path, load_config, save_config
from output import emit, emit_error

VERSION = "0.1.0-m1"
WORKSPACE_ROOT_OVERRIDE: Path | None = None
SUMMARY_FIELDS = ("id", "name", "description", "status", "level", "node_type")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _config_path() -> Path:
    return default_config_path(workspace_root=WORKSPACE_ROOT_OVERRIDE)


def _load() -> Config:
    return load_config(_config_path())


def _store():
    cfg = _load()
    if not cfg.initialized:
        emit_error("not initialized - run `memory_cli.py init` first", code="uninitialized")

    from cozo_store import CozoStore
    from embedding import get_provider

    provider = None
    try:
        provider = get_provider(cfg.embedding_provider)
    except Exception:
        provider = None

    store = CozoStore(db_path=cfg.expanded_db_path(), embedding_provider=provider)
    store.ensure_schema()
    return store, cfg


def _project(opt_project: str | None, cfg: Config) -> str:
    project = opt_project or cfg.default_project
    if not project:
        emit_error("no project specified and no default_project configured", code="missing_project")
    return project


def _node_payloads(nodes: Iterable[object], *, summary: bool = False) -> list[dict]:
    payloads = [n.to_dict() if hasattr(n, "to_dict") else n for n in nodes]
    if not summary:
        return payloads
    return [{key: payload[key] for key in SUMMARY_FIELDS if key in payload} for payload in payloads]


def _scratchpad():
    from scratchpad import ScratchpadStore

    cfg = _load()
    storage_dir = Path(cfg.expanded_db_path()).parent
    return ScratchpadStore(storage_dir / "scratchpad.json")


@click.group()
@click.option(
    "--workspace-root",
    type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
    help="Override detected workspace root for .superpowers/pyramid-memory.",
)
@click.pass_context
def cli(ctx: click.Context, workspace_root: Path | None) -> None:
    """Pyramid Memory: graph + decision storage for AI-driven decomposition."""
    global WORKSPACE_ROOT_OVERRIDE
    WORKSPACE_ROOT_OVERRIDE = workspace_root
    ctx.ensure_object(dict)
    ctx.obj["workspace_root"] = workspace_root


@cli.command()
def version() -> None:
    """Print CLI version."""
    emit({"version": VERSION})


@cli.command()
@click.option("--project", required=True, help="Default project name (namespace).")
@click.option(
    "--embedding",
    type=click.Choice(["skip", "fastembed", "voyage", "openai", "ollama"]),
    default="skip",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path, dir_okay=False, resolve_path=True),
    default=None,
    help="Override database file path. Defaults to <workspace-root>/.superpowers/pyramid-memory/data.cozo.",
)
@click.option("--non-interactive", is_flag=True, help="Skip prompts (for tests/scripts).")
def init(project: str, embedding: str, db_path: Path | None, non_interactive: bool) -> None:
    """Initialize the pyramid memory store."""
    resolved_db_path = db_path or default_db_path(workspace_root=WORKSPACE_ROOT_OVERRIDE)
    cfg = Config(
        embedding_provider=embedding,
        db_path=str(resolved_db_path),
        default_project=project,
        initialized=True,
    )
    save_config(_config_path(), cfg)

    from cozo_store import CozoStore

    store = CozoStore(db_path=cfg.expanded_db_path())
    store.ensure_schema()

    emit(
        {
            "initialized": True,
            "project": project,
            "embedding": embedding,
            "db_path": cfg.expanded_db_path(),
        }
    )


@cli.group()
def config() -> None:
    """Inspect or modify configuration."""


@config.command("show")
def config_show() -> None:
    """Show current configuration as JSON."""
    cfg = _load()
    emit(
        {
            "initialized": cfg.initialized,
            "embedding_provider": cfg.embedding_provider,
            "db_path": cfg.expanded_db_path(),
            "default_project": cfg.default_project,
            "display_tree_format": cfg.display_tree_format,
            "scan_last_commit": cfg.scan_last_commit,
            "scan_project_root": cfg.scan_project_root,
        }
    )


@config.command("set")
@click.option("--key", "key_opt")
@click.option("--value", "value_opt")
@click.argument("args", nargs=-1)
def config_set(key_opt: str | None, value_opt: str | None, args: tuple[str, ...]) -> None:
    """Set a configuration value."""
    if key_opt is not None and value_opt is not None:
        key, value = key_opt, value_opt
    elif len(args) == 2:
        key, value = args
    else:
        emit_error("config set requires key and value", code="invalid_config_args")

    cfg = _load()
    if key not in {
        "embedding_provider",
        "default_project",
        "db_path",
        "display.tree_format",
        "scan.last_commit",
        "scan.project_root",
    }:
        emit_error(f"unknown config key: {key}")
    if key == "db_path":
        value = str(Path(value).expanduser().resolve())
        setattr(cfg, key, value)
    elif key == "display.tree_format":
        if value not in {"ascii", "mermaid"}:
            emit_error("display.tree_format must be one of: ascii, mermaid", code="invalid_config_value")
        cfg.display_tree_format = value
    elif key == "scan.last_commit":
        cfg.scan_last_commit = value
    elif key == "scan.project_root":
        cfg.scan_project_root = str(Path(value).expanduser().resolve())
        value = cfg.scan_project_root
    else:
        setattr(cfg, key, value)
    save_config(_config_path(), cfg)
    emit({"updated": {key: value}})


@cli.group()
def node() -> None:
    """Node CRUD."""


@node.command("create")
@click.option("--id", "node_id", required=True)
@click.option("--name", required=True)
@click.option(
    "--type",
    "node_type",
    type=click.Choice(
        ["root", "branch", "leaf", "existing_module", "change_root", "change_branch", "change_leaf"]
    ),
    required=True,
)
@click.option("--level", type=int, required=True)
@click.option("--description", required=True)
@click.option("--origin", type=click.Choice(["user_stated", "skill_inferred"]), required=True)
@click.option("--status", default="draft")
@click.option("--tokens-estimate", type=int, default=0)
@click.option("--project")
def node_create(
    node_id: str,
    name: str,
    node_type: str,
    level: int,
    description: str,
    origin: str,
    status: str,
    tokens_estimate: int,
    project: str | None,
) -> None:
    from models import Node

    store, cfg = _store()
    p = _project(project, cfg)
    now = _now()
    node_obj = Node(
        id=node_id,
        project=p,
        name=name,
        node_type=node_type,
        level=level,
        description=description,
        status=status,
        origin=origin,
        tokens_estimate=tokens_estimate,
        created_at=now,
        updated_at=now,
    )
    store.create_node(node_obj)
    emit(node_obj.to_dict())


@node.command("get")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def node_get(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    node_obj = store.get_node(p, node_id)
    emit(node_obj.to_dict())


@node.command("update")
@click.option("--id", "node_id", required=True)
@click.option("--status")
@click.option("--description")
@click.option("--tokens-estimate", type=int)
@click.option(
    "--criteria-confirmed",
    is_flag=True,
    help="Required when transitioning to status=leaf; runs mechanical checks.",
)
@click.option("--project")
def node_update(
    node_id: str,
    status: str | None,
    description: str | None,
    tokens_estimate: int | None,
    criteria_confirmed: bool,
    project: str | None,
) -> None:
    store, cfg = _store()
    p = _project(project, cfg)

    if status == "leaf":
        if not criteria_confirmed:
            emit_error(
                "transitioning to status=leaf requires --criteria-confirmed "
                "(run `memory check-leaf-criteria --node X` first, then re-invoke with the flag)",
                code="criteria_not_confirmed",
            )
        report = store.check_leaf_criteria(p, node_id)
        if not report["mechanical_checks_pass"]:
            failed = [c for c in report["criteria"] if c.get("passes") is False]
            messages = "; ".join(f"{c['criterion']}: {c['reason']}" for c in failed)
            emit_error(
                f"mechanical leaf criteria failed: {messages}",
                code="criteria_failed",
            )

    fields: dict[str, object] = {"updated_at": _now()}
    if status is not None:
        fields["status"] = status
    if description is not None:
        fields["description"] = description
    if tokens_estimate is not None:
        fields["tokens_estimate"] = tokens_estimate

    node_obj = store.update_node(p, node_id, **fields)
    emit(node_obj.to_dict())


@node.command("delete")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def node_delete(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    store.delete_node(p, node_id)
    emit({"deleted": node_id})


@node.command("list")
@click.option("--status")
@click.option("--level", type=int, default=None)
@click.option("--summary", is_flag=True)
@click.option("--project")
def node_list(status: str | None, level: int | None, summary: bool, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.list_nodes(p, status=status, level=level)
    emit({"nodes": _node_payloads(nodes, summary=summary)})


@cli.group()
def edge() -> None:
    """Edge add/remove."""


@edge.command("add")
@click.option("--kind", type=click.Choice(["hierarchy", "dependency"]), required=True)
@click.option("--from", "from_id", required=True)
@click.option("--to", "to_id", required=True)
@click.option("--order", "order_idx", type=int, default=0)
@click.option("--dep-type", default="requires")
def edge_add(kind: str, from_id: str, to_id: str, order_idx: int, dep_type: str) -> None:
    from models import Edge

    store, _ = _store()
    store.add_edge(Edge(kind=kind, from_id=from_id, to_id=to_id, order_idx=order_idx, dep_type=dep_type))
    emit({"added": {"kind": kind, "from": from_id, "to": to_id}})


@edge.command("remove")
@click.option("--kind", type=click.Choice(["hierarchy", "dependency"]), required=True)
@click.option("--from", "from_id", required=True)
@click.option("--to", "to_id", required=True)
def edge_remove(kind: str, from_id: str, to_id: str) -> None:
    store, _ = _store()
    store.remove_edge(kind, from_id, to_id)
    emit({"removed": {"kind": kind, "from": from_id, "to": to_id}})


@cli.group()
def query() -> None:
    """Graph traversals."""


@query.command("children")
@click.option("--id", "node_id", required=True)
@click.option("--summary", is_flag=True)
@click.option("--project")
def query_children(node_id: str, summary: bool, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_children(p, node_id)
    emit({"nodes": _node_payloads(nodes, summary=summary)})


@query.command("ancestors")
@click.option("--id", "node_id", required=True)
@click.option("--summary", is_flag=True)
@click.option("--project")
def query_ancestors(node_id: str, summary: bool, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_ancestors(p, node_id)
    emit({"nodes": _node_payloads(nodes, summary=summary)})


@query.command("subtree")
@click.option("--root", "root_id", required=True)
@click.option("--summary", is_flag=True)
@click.option("--project")
def query_subtree(root_id: str, summary: bool, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_subtree(p, root_id)
    emit({"nodes": _node_payloads(nodes, summary=summary)})


@query.command("deps")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_deps(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_deps(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("deps-of")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_deps_of(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_reverse_deps(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("impact")
@click.option("--id", "node_id", required=True)
@click.option("--direction", type=click.Choice(["upstream", "downstream"]), default="downstream")
@click.option("--project")
def query_impact(node_id: str, direction: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_impact_closure(p, node_id, direction=direction)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("cycles")
@click.option("--project")
def query_cycles(project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    cycles = store.detect_cycles(p)
    emit({"cycles": cycles})


@cli.group()
def decision() -> None:
    """Decision logging."""


@decision.command("store")
@click.option("--id", "decision_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--question", required=True)
@click.option("--options", required=True, help="JSON-encoded list")
@click.option("--chosen", required=True)
@click.option("--reasoning", required=True)
@click.option("--tradeoffs", default="")
def decision_store(
    decision_id: str,
    node_id: str,
    question: str,
    options: str,
    chosen: str,
    reasoning: str,
    tradeoffs: str,
) -> None:
    from models import Decision

    store, _ = _store()
    decision_obj = Decision(
        id=decision_id,
        node_id=node_id,
        question=question,
        options=options,
        chosen=chosen,
        reasoning=reasoning,
        tradeoffs=tradeoffs,
        created_at=_now(),
    )
    store.store_decision(decision_obj)
    emit(decision_obj.to_dict())


@decision.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def decision_list(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    decisions = store.list_decisions(p, node_id)
    emit({"decisions": [d.to_dict() for d in decisions]})


@cli.group()
def interface() -> None:
    """Interface capture."""


@interface.command("add")
@click.option("--id", "iface_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--name", required=True)
@click.option("--description", required=True)
@click.option("--spec", required=True)
def interface_add(iface_id: str, node_id: str, name: str, description: str, spec: str) -> None:
    from models import Interface

    store, _ = _store()
    iface = Interface(
        id=iface_id,
        node_id=node_id,
        name=name,
        description=description,
        spec=spec,
        created_at=_now(),
    )
    store.add_interface(iface)
    emit(iface.to_dict())


@interface.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def interface_list(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    interfaces = store.list_interfaces(p, node_id)
    emit({"interfaces": [i.to_dict() for i in interfaces]})


@cli.group("file-ref")
def file_ref_group() -> None:
    """Manage code file references attached to nodes."""


@file_ref_group.command("add")
@click.option("--id", "ref_id", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--path", "file_path", required=True)
@click.option("--lines", default="*")
@click.option("--role", required=True, type=click.Choice(["modify", "read", "test", "create"]))
@click.option("--content-hash", required=True)
@click.option("--status", default="current", type=click.Choice(["current", "stale", "deleted"]))
@click.option("--project")
def file_ref_add(
    ref_id: str,
    node_id: str,
    file_path: str,
    lines: str,
    role: str,
    content_hash: str,
    status: str,
    project: str | None,
) -> None:
    from models import FileRef

    store, cfg = _store()
    p = _project(project, cfg)
    store.get_node(p, node_id)
    file_ref = FileRef(
        id=ref_id,
        node_id=node_id,
        path=file_path,
        lines=lines,
        role=role,
        content_hash=content_hash,
        scanned_at=_now(),
        status=status,
    )
    store.add_file_ref(file_ref)
    emit({"file_ref_id": ref_id})


@file_ref_group.command("list")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def file_ref_list(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    refs = store.list_file_refs(p, node_id)
    emit({"file_refs": [ref.to_dict() for ref in refs]})


@file_ref_group.command("check")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def file_ref_check(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    emit(store.check_file_refs(p, node_id))


@cli.group("scratch")
def scratch_group() -> None:
    """Session scratchpad for in-conversation findings."""


@scratch_group.command("write")
@click.option("--key", required=True)
@click.option("--value", required=True)
@click.option("--category", default="session_keep", type=click.Choice(["must_persist", "session_keep"]))
@click.option("--ttl", default="session", type=click.Choice(["session", "persist"]))
def scratch_write(key: str, value: str, category: str, ttl: str) -> None:
    from models import ScratchEntry

    scratchpad = _scratchpad()
    scratchpad.write(
        ScratchEntry(key=key, value=value, category=category, ttl=ttl, created_at=_now())
    )
    emit({"key": key, "written": True})


@scratch_group.command("list")
@click.option("--category", default=None, type=click.Choice(["must_persist", "session_keep"]))
def scratch_list(category: str | None) -> None:
    scratchpad = _scratchpad()
    entries = scratchpad.list_all(category=category)
    emit({"entries": [entry.to_dict() for entry in entries], "count": len(entries)})


@scratch_group.command("promote")
@click.option("--key", required=True)
@click.option("--node", "node_id", required=True)
@click.option("--as", "promote_as", required=True, type=click.Choice(["decision", "interface"]))
@click.option("--project")
def scratch_promote(key: str, node_id: str, promote_as: str, project: str | None) -> None:
    scratchpad = _scratchpad()
    entries = [entry for entry in scratchpad.list_all() if entry.key == key]
    if not entries:
        emit_error(f"scratchpad key not found: {key}", code="not_found")

    entry = entries[0]
    store, cfg = _store()
    _project(project, cfg)

    import uuid

    if promote_as == "decision":
        from models import Decision

        store.store_decision(
            Decision(
                id=f"scratch-{key}-{uuid.uuid4().hex[:8]}",
                node_id=node_id,
                question=f"Session finding: {key}",
                options="[]",
                chosen=entry.value,
                reasoning=entry.value,
                tradeoffs="Promoted from session scratchpad",
                created_at=_now(),
            )
        )
    else:
        from models import Interface

        store.add_interface(
            Interface(
                id=f"scratch-{key}-{uuid.uuid4().hex[:8]}",
                node_id=node_id,
                name=key,
                description=f"Discovered during session: {key}",
                spec=entry.value,
                created_at=_now(),
            )
        )

    scratchpad.delete(key)
    emit({"key": key, "node_id": node_id, "promoted_as": promote_as})


@scratch_group.command("clear")
@click.option(
    "--ttl",
    default=None,
    type=click.Choice(["session", "persist"]),
    help="Only clear entries with this TTL. Omit to clear all.",
)
def scratch_clear(ttl: str | None) -> None:
    scratchpad = _scratchpad()
    before = len(scratchpad.list_all())
    scratchpad.clear(ttl=ttl)
    after = len(scratchpad.list_all())
    emit({"cleared": before - after, "remaining": after})


@cli.group()
def memory() -> None:
    """Recall, context assembly, validation, maintenance."""


@memory.command("recall")
@click.option("--query", required=True)
@click.option("--k", type=int, default=5)
@click.option("--semantic/--no-semantic", default=False)
@click.option("--project")
def memory_recall(query: str, k: int, semantic: bool, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)

    requested_semantic = semantic
    degraded = False
    warnings: list[str] = []
    if requested_semantic:
        if cfg.embedding_provider == "skip":
            warnings.append("semantic requested but embedding_provider=skip; falling back to BM25")
            semantic = False
            degraded = True
        elif getattr(store, "embedding_provider", None) is None:
            warnings.append("semantic requested but embedding provider unavailable; falling back to BM25")
            semantic = False
            degraded = True

    matches = store.recall(p, query=query, k=k, semantic=semantic)
    if requested_semantic and any(m.match_type != "semantic" for m in matches):
        degraded = True
        if not warnings:
            warnings.append("semantic recall degraded; using BM25 results")
    emit(
        {
            "matches": [
                {
                    "node": m.node.to_dict(),
                    "score": m.score,
                    "match_type": m.match_type,
                }
                for m in matches
            ]
        },
        warnings=warnings,
        degraded=degraded,
    )


@memory.command("context")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def memory_context(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    pkg = store.assemble_context(p, node_id)
    emit(pkg.to_dict())


@memory.command("check-leaf-criteria")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def memory_check_leaf_criteria(node_id: str, project: str | None) -> None:
    """Report all 5 independence criteria for a node."""
    store, cfg = _store()
    p = _project(project, cfg)
    report = store.check_leaf_criteria(p, node_id)
    emit(report, ok=report["mechanical_checks_pass"])


@memory.command("validate")
@click.option("--project")
def memory_validate(project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    emit(store.validate(p))


@memory.command("stats")
@click.option("--project")
def memory_stats(project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    emit(store.stats(p))


@memory.command("hotspots")
@click.option("--days", type=int, default=90)
@click.option("--top", type=int, default=20)
def memory_hotspots(days: int, top: int) -> None:
    from git_utils import git_change_hotspots

    cfg = _load()
    project_root = Path(cfg.scan_project_root) if cfg.scan_project_root else Path.cwd()
    try:
        hotspots = git_change_hotspots(project_root, days=days, top=top)
    except Exception as exc:
        emit_error(f"unable to compute git hotspots: {exc}", code="git_hotspots_failed")
    emit({"project_root": str(project_root), "hotspots": hotspots})


@memory.command("doctor")
def memory_doctor() -> None:
    """Health check for store and embedding provider."""
    cfg = _load()
    db_ok = False
    embedding_ok = cfg.embedding_provider == "skip"
    notes: list[str] = []

    if not cfg.initialized:
        notes.append("not initialized")
    else:
        try:
            from cozo_store import CozoStore

            CozoStore(db_path=cfg.expanded_db_path()).ensure_schema()
            db_ok = True
        except Exception as exc:
            notes.append(f"db error: {exc}")

        if cfg.embedding_provider != "skip":
            try:
                from embedding import get_provider

                provider = get_provider(cfg.embedding_provider)
                provider.embed(["healthcheck"])
                embedding_ok = True
            except Exception as exc:
                notes.append(f"embedding error: {exc}")

    emit(
        {
            "initialized": cfg.initialized,
            "db_ok": db_ok,
            "embedding_provider": cfg.embedding_provider,
            "embedding_ok": embedding_ok,
            "notes": notes,
        }
    )


@memory.command("freshness")
@click.option("--project")
def memory_freshness(project: str | None) -> None:
    store, cfg = _store()
    _project(project, cfg)
    if not cfg.scan_last_commit or not cfg.scan_project_root:
        emit({"status": "unknown", "reason": "no scan config", "changed_files": []})
        return

    from git_utils import git_changed_files, git_head_sha

    project_root = Path(cfg.scan_project_root)
    current_head = git_head_sha(project_root)
    if current_head == cfg.scan_last_commit:
        emit(
            {
                "status": "fresh",
                "last_commit": cfg.scan_last_commit,
                "head": current_head,
                "changed_files": [],
            }
        )
        return

    changed = git_changed_files(project_root, cfg.scan_last_commit)
    emit(
        {
            "status": "stale",
            "last_commit": cfg.scan_last_commit,
            "head": current_head,
            "changed_files": changed,
            "changed_count": len(changed),
        }
    )


@memory.command("refresh")
@click.option("--project")
def memory_refresh(project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    if not cfg.scan_last_commit or not cfg.scan_project_root:
        emit_error(
            "no scan config - run freshness first or set scan.last_commit + scan.project_root",
            code="no_scan_config",
        )

    from git_utils import git_changed_files, git_head_sha

    project_root = Path(cfg.scan_project_root)
    current_head = git_head_sha(project_root)
    if current_head == cfg.scan_last_commit:
        emit({"marked_stale": 0, "stale_paths": [], "message": "already fresh"})
        return

    changed_files = set(git_changed_files(project_root, cfg.scan_last_commit))
    marked_stale = 0
    stale_paths: list[str] = []
    for node in store.list_nodes(p):
        for file_ref in store.list_file_refs(p, node.id):
            if file_ref.status == "current" and file_ref.path in changed_files:
                store.update_file_ref(file_ref.id, status="stale", scanned_at=_now())
                marked_stale += 1
                stale_paths.append(file_ref.path)

    cfg.scan_last_commit = current_head
    save_config(_config_path(), cfg)
    emit({"marked_stale": marked_stale, "stale_paths": stale_paths, "new_last_commit": current_head})


@memory.command("reindex")
@click.option("--project")
def memory_reindex(project: str | None) -> None:
    """Recompute embeddings for all nodes in a project."""
    store, cfg = _store()
    if cfg.embedding_provider == "skip":
        emit_error("cannot reindex with embedding_provider=skip")

    p = _project(project, cfg)
    nodes = store.list_nodes(p)
    count = 0
    for node_obj in nodes:
        try:
            store.update_node(p, node_obj.id, updated_at=_now())
            count += 1
        except Exception:
            pass
    emit({"reindexed": count})


@memory.command("recompute-tokens")
@click.option("--node", "node_id", required=True)
@click.option("--project")
def memory_recompute_tokens(node_id: str, project: str | None) -> None:
    """Recompute a node's tokens_estimate from live context assembly."""
    store, cfg = _store()
    p = _project(project, cfg)
    pkg = store.assemble_context(p, node_id)
    new_estimate = pkg.tokens_estimate
    store.update_node(p, node_id, tokens_estimate=new_estimate, updated_at=_now())
    emit({"node_id": node_id, "tokens_estimate": new_estimate})


def _default_tree_root(store, project: str) -> str:
    nodes = store.list_nodes(project)
    root_nodes = sorted(
        [node for node in nodes if node.node_type == "root"],
        key=lambda node: (node.level, node.created_at, node.id),
    )
    if root_nodes:
        return root_nodes[0].id
    if not nodes:
        emit_error("no nodes exist for project", code="missing_root")
    return sorted(nodes, key=lambda node: (node.level, node.created_at, node.id))[0].id


def _tree_data(store, project: str, root_id: str) -> tuple[dict[str, object], dict[str, list[str]]]:
    subtree_nodes = store.query_subtree(project, root_id)
    nodes_by_id = {node.id: node for node in subtree_nodes}
    children: dict[str, list[str]] = {}
    for node in subtree_nodes:
        child_nodes = [child.id for child in store.query_children(project, node.id) if child.id in nodes_by_id]
        children[node.id] = child_nodes
    return nodes_by_id, children


@memory.command("tree")
@click.option("--root", "root_id", default=None, help="Root node ID. Defaults to the project's root node.")
@click.option(
    "--format",
    "fmt",
    default=None,
    type=click.Choice(["ascii", "mermaid"]),
    help="Output format. Defaults to config display_tree_format.",
)
@click.option("--show-deps", is_flag=True, help="Include dependency edges in Mermaid output.")
@click.option("--project")
def memory_tree(root_id: str | None, fmt: str | None, show_deps: bool, project: str | None) -> None:
    from tree_renderer import render_ascii, render_mermaid

    store, cfg = _store()
    p = _project(project, cfg)
    actual_root = root_id or _default_tree_root(store, p)
    nodes_by_id, children = _tree_data(store, p, actual_root)
    dep_edges: list[tuple[str, str]] = []
    if show_deps:
        for node_id in nodes_by_id:
            for dep_node in store.query_deps(p, node_id):
                if dep_node.id in nodes_by_id:
                    dep_edges.append((node_id, dep_node.id))

    actual_format = fmt or cfg.display_tree_format
    if actual_format == "mermaid":
        tree = render_mermaid(actual_root, nodes_by_id, children, dep_edges=dep_edges)
    else:
        tree = render_ascii(actual_root, nodes_by_id, children)
    emit({"tree": tree, "format": actual_format, "root": actual_root})


@memory.command("export")
@click.option("--project")
def memory_export(project: str | None) -> None:
    """Export project memory payload as JSON object."""
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = [n.to_dict() for n in store.list_nodes(p)]
    decisions: list[dict] = []
    interfaces: list[dict] = []
    for n in nodes:
        decisions.extend(d.to_dict() for d in store.list_decisions(p, n["id"]))
        interfaces.extend(i.to_dict() for i in store.list_interfaces(p, n["id"]))
    emit({"nodes": nodes, "decisions": decisions, "interfaces": interfaces})


if __name__ == "__main__":
    cli()
