"""Prove that BFS-style context loading stays bounded as the tree grows."""

import json


def test_context_at_each_level_stays_bounded(run_cli):
    cli = run_cli
    cli("init", "--project", "budget", "--embedding", "skip", "--non-interactive")

    cli(
        "node",
        "create",
        "--id",
        "root",
        "--name",
        "system",
        "--type",
        "root",
        "--level",
        "0",
        "--description",
        "a large system with many modules",
        "--origin",
        "user_stated",
    )

    l1_ids = []
    for i in range(4):
        nid = f"l1-{i}"
        l1_ids.append(nid)
        cli(
            "node",
            "create",
            "--id",
            nid,
            "--name",
            f"module-{i}",
            "--type",
            "branch",
            "--level",
            "1",
            "--description",
            f"module {i} handles feature {i}",
            "--origin",
            "user_stated",
        )
        cli("edge", "add", "--kind", "hierarchy", "--from", "root", "--to", nid)
        cli(
            "decision",
            "store",
            "--id",
            f"d-{nid}",
            "--node",
            "root",
            "--question",
            "split?",
            "--options",
            "[]",
            "--chosen",
            nid,
            "--reasoning",
            f"module {i} is independent",
        )

    l2_ids = []
    for l1 in l1_ids:
        for j in range(3):
            nid = f"{l1}-sub-{j}"
            l2_ids.append(nid)
            cli(
                "node",
                "create",
                "--id",
                nid,
                "--name",
                f"sub-{j}",
                "--type",
                "branch",
                "--level",
                "2",
                "--description",
                f"sub-component {j} of {l1}",
                "--origin",
                "skill_inferred",
            )
            cli("edge", "add", "--kind", "hierarchy", "--from", l1, "--to", nid)
            cli(
                "decision",
                "store",
                "--id",
                f"d-{nid}",
                "--node",
                l1,
                "--question",
                "split?",
                "--options",
                "[]",
                "--chosen",
                nid,
                "--reasoning",
                f"component {j} is separable",
            )

    for l2 in l2_ids:
        for k in range(2):
            nid = f"{l2}-leaf-{k}"
            cli(
                "node",
                "create",
                "--id",
                nid,
                "--name",
                f"leaf-{k}",
                "--type",
                "leaf",
                "--level",
                "3",
                "--description",
                f"implement leaf {k} of {l2}",
                "--origin",
                "skill_inferred",
            )
            cli("edge", "add", "--kind", "hierarchy", "--from", l2, "--to", nid)

    max_context_chars = 12000

    root_full = json.loads(cli("node", "get", "--id", "root", "--project", "budget").stdout)["data"]
    l1_summaries = json.loads(
        cli("node", "list", "--project", "budget", "--level", "1", "--summary").stdout
    )["data"]["nodes"]
    level1_chars = len(json.dumps(root_full)) + len(json.dumps(l1_summaries))
    assert level1_chars < max_context_chars, f"Level 1 context: {level1_chars} chars"

    ancestors = json.loads(
        cli("query", "ancestors", "--project", "budget", "--id", "l1-0-sub-0", "--summary").stdout
    )["data"]["nodes"]
    current_full = json.loads(
        cli("node", "get", "--project", "budget", "--id", "l1-0-sub-0").stdout
    )["data"]
    l2_siblings = json.loads(
        cli("node", "list", "--project", "budget", "--level", "2", "--summary").stdout
    )["data"]["nodes"]
    level2_chars = len(json.dumps(ancestors)) + len(json.dumps(current_full)) + len(
        json.dumps(l2_siblings)
    )
    assert level2_chars < max_context_chars, f"Level 2 context: {level2_chars} chars"

    leaf_id = f"{l2_ids[0]}-leaf-0"
    ancestors3 = json.loads(
        cli("query", "ancestors", "--project", "budget", "--id", leaf_id, "--summary").stdout
    )["data"]["nodes"]
    current3 = json.loads(cli("node", "get", "--project", "budget", "--id", leaf_id).stdout)["data"]
    l3_siblings = json.loads(
        cli("node", "list", "--project", "budget", "--level", "3", "--summary").stdout
    )["data"]["nodes"]
    level3_chars = len(json.dumps(ancestors3)) + len(json.dumps(current3)) + len(
        json.dumps(l3_siblings)
    )
    assert level3_chars < max_context_chars, f"Level 3 context: {level3_chars} chars"

    all_nodes = json.loads(cli("node", "list", "--project", "budget").stdout)["data"]["nodes"]
    assert len(all_nodes) == 41
