## 2026-04-09 — Eval 01 (simple_blog)

- Status: PASS
- total_nodes: 9
- leaves: 5
- decisions: 3
- skill_inferred_ratio: 0.33
- Notes: Executed in a sandboxed local session using isolated `HOME=/tmp/pyramid-evals`.

## 2026-04-09 — Eval 02 (ecommerce)

- Status: PASS
- total_nodes: 16
- leaves: 9
- decisions: 7
- skill_inferred_ratio: 0.31
- Notes: Verified cross-leaf dependency modeling around checkout, payment, inventory, and tax.

## 2026-04-09 — Eval 03 (data_pipeline)

- Status: PASS
- total_nodes: 12
- leaves: 7
- decisions: 4
- skill_inferred_ratio: 0.42
- Notes: Verified dependency-heavy extract -> transform -> load style flow and inferred operational concerns.

## AC #2 — cross-harness shared memory

- Tested harnesses: simulated fresh shell with `unset PYTHONPATH` and workspace-local store rooted in `/tmp/pyramid-evals/.superpowers/pyramid-memory/`
- Shared workspace-local memory: confirmed within the simulated shell boundary
- Status: PASS (fresh-shell simulation)

## AC #4 — fuzzy requirement -> confirmed pyramid (no user-written spec)

- Verified by evals 01, 02, 03
- All 3 scenarios PASS
- User input remained a short fuzzy requirement in each scenario
- Status: PASS
