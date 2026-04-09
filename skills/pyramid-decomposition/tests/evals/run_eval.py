#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Eval runner for pyramid decomposition scenarios."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[3] / "memory-management" / "scripts"
CONFIG_PATH = Path(".superpowers") / "pyramid-memory" / "config.toml"


def cli(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_memory_cli.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        raise SystemExit(result.stderr.strip() or f"command failed: {' '.join(args)}")
    return json.loads(result.stdout)


def parse_assertions(scenario_path: Path) -> dict:
    text = scenario_path.read_text()
    match = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise SystemExit(f"no YAML assertions block found in {scenario_path}")
    return yaml.safe_load(match.group(1))


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: run_eval.py <scenario.md>")
        raise SystemExit(1)

    scenario = Path(sys.argv[1])
    asserts = parse_assertions(scenario)
    project_should_exist = asserts.get("project_should_exist", True)
    config_exists = CONFIG_PATH.exists()

    failures: list[str] = []
    if "expect_memory_config" in asserts:
        if bool(config_exists) != bool(asserts["expect_memory_config"]):
            failures.append(
                f"memory config exists={config_exists} expected {asserts['expect_memory_config']}"
            )

    if not project_should_exist:
        if config_exists:
            project = asserts.get("project")
            if project:
                try:
                    stats_payload = cli("memory", "stats", "--project", project)
                    total_nodes = stats_payload["data"]["total_nodes"]
                    if total_nodes > 0:
                        failures.append(f"unexpected pyramid state: total_nodes={total_nodes}")
                except SystemExit:
                    pass
        if failures:
            print(f"FAIL: {scenario.name}")
            for failure in failures:
                print(f"  - {failure}")
            raise SystemExit(1)
        print(f"PASS: {scenario.name}")
        print("  pyramid not activated, as expected")
        return

    project = asserts["project"]

    stats = cli("memory", "stats", "--project", project)["data"]
    nodes = cli("node", "list", "--project", project)["data"]["nodes"]
    leaf_count = sum(1 for n in nodes if n["status"] == "leaf")
    config = cli("config", "show")["data"]

    decision_count = 0
    file_ref_count = 0
    for node in nodes:
        decision_count += len(
            cli("decision", "list", "--node", node["id"], "--project", project)["data"]["decisions"]
        )
        file_ref_count += len(
            cli("file-ref", "list", "--node", node["id"], "--project", project)["data"]["file_refs"]
        )

    validation = cli("memory", "validate", "--project", project)["data"]
    cycles = cli("query", "cycles", "--project", project)["data"]["cycles"]
    haystack = " ".join((n["name"] + " " + n["description"]).lower() for n in nodes)
    missing_concepts = [c for c in asserts.get("expected_concepts", []) if c.lower() not in haystack]
    node_types = {n["node_type"] for n in nodes}

    if not (asserts["min_total_nodes"] <= stats["total_nodes"] <= asserts["max_total_nodes"]):
        failures.append(
            f"total_nodes={stats['total_nodes']} not in "
            f"[{asserts['min_total_nodes']}, {asserts['max_total_nodes']}]"
        )
    if leaf_count < asserts["min_leaf_count"]:
        failures.append(f"leaf_count={leaf_count} < {asserts['min_leaf_count']}")
    if decision_count < asserts["min_decisions"]:
        failures.append(f"decision_count={decision_count} < {asserts['min_decisions']}")
    if stats["skill_inferred_node_ratio"] < asserts["min_skill_inferred_ratio"]:
        failures.append(
            "skill_inferred_ratio="
            f"{stats['skill_inferred_node_ratio']:.2f} < {asserts['min_skill_inferred_ratio']}"
        )
    if validation["passed"] != asserts["validate_passes"]:
        failures.append(
            f"validate.passed={validation['passed']} != expected {asserts['validate_passes']}"
        )
    if (len(cycles) == 0) != asserts["no_cycles"]:
        failures.append(f"cycles={len(cycles)} expected no_cycles={asserts['no_cycles']}")
    if missing_concepts:
        failures.append(f"missing concepts: {missing_concepts}")
    for node_type in asserts.get("expected_node_types", []):
        if node_type not in node_types:
            failures.append(f"missing node type: {node_type}")
    if file_ref_count < asserts.get("min_file_refs", 0):
        failures.append(f"file_ref_count={file_ref_count} < {asserts['min_file_refs']}")
    if asserts.get("require_scan_metadata"):
        if not config.get("scan_last_commit"):
            failures.append("scan_last_commit missing")
        if not config.get("scan_project_root"):
            failures.append("scan_project_root missing")

    if failures:
        print(f"FAIL: {scenario.name}")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print(f"PASS: {scenario.name}")
    print(
        f"  total={stats['total_nodes']} leaves={leaf_count} "
        f"decisions={decision_count} file_refs={file_ref_count} "
        f"inferred_ratio={stats['skill_inferred_node_ratio']:.2f}"
    )


if __name__ == "__main__":
    main()
