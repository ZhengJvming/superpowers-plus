from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SKILLS = REPO / "skills"


def _read(path: str) -> str:
    return (SKILLS / path / "SKILL.md").read_text()


def test_using_superpowers_declares_three_route_classes():
    text = _read("using-superpowers")
    assert "## Route by Task Size" in text
    assert "### Simple / Local" in text
    assert "### Bounded Multi-Step" in text
    assert "### Large / Fuzzy / Cross-Boundary" in text
    assert "Use the lightest workflow that can safely handle the task." in text


def test_using_superpowers_includes_analysis_and_refactor_routes():
    text = _read("using-superpowers")
    assert "### Analytical / Review" in text
    assert "codebase-exploration" in text
    assert "### Refactoring" in text


def test_brainstorming_allows_direct_route_for_trivial_changes():
    text = _read("brainstorming")
    assert "## Route Gate" in text
    assert "Do not use this skill for a trivially bounded local change." in text
    assert "If you were invoked anyway" in text
    assert "switch into `pyramid-decomposition`" in text


def test_brainstorming_accepts_debugging_handoff():
    text = _read("brainstorming")
    assert "Inbound from Debugging Escalation" in text
    assert "read scratchpad findings first" in text


def test_writing_plans_rejects_trivial_one_loop_work():
    text = _read("writing-plans")
    assert "Do not write a full plan for a trivially bounded change." in text
    assert "route back to the direct implementation path" in text


def test_codebase_exploration_supports_standalone_review_mode():
    text = _read("codebase-exploration")
    assert "standalone architecture review" in text
    assert "dependency" in text
    assert "hotspots" in text
