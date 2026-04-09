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

import click

from config import Config, default_config_path, default_db_path, load_config, save_config
from output import emit, emit_error

VERSION = "0.1.0-m1"
WORKSPACE_ROOT_OVERRIDE: Path | None = None


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
        }
    )


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    cfg = _load()
    if key not in {"embedding_provider", "default_project", "db_path"}:
        emit_error(f"unknown config key: {key}")
    if key == "db_path":
        value = str(Path(value).expanduser().resolve())
    setattr(cfg, key, value)
    save_config(_config_path(), cfg)
    emit({"updated": {key: value}})


@cli.group()
def node() -> None:
    """Node CRUD."""


@node.command("create")
@click.option("--id", "node_id", required=True)
@click.option("--name", required=True)
@click.option("--type", "node_type", type=click.Choice(["root", "branch", "leaf"]), required=True)
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
@click.option("--project")
def node_list(status: str | None, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.list_nodes(p, status=status)
    emit({"nodes": [n.to_dict() for n in nodes]})


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
@click.option("--project")
def query_children(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_children(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("ancestors")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_ancestors(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_ancestors(p, node_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("subtree")
@click.option("--root", "root_id", required=True)
@click.option("--project")
def query_subtree(root_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_subtree(p, root_id)
    emit({"nodes": [n.to_dict() for n in nodes]})


@query.command("deps")
@click.option("--id", "node_id", required=True)
@click.option("--project")
def query_deps(node_id: str, project: str | None) -> None:
    store, cfg = _store()
    p = _project(project, cfg)
    nodes = store.query_deps(p, node_id)
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
