# Pyramid Decomposition Evals

These scenarios verify both routing and decomposition quality:
- simple tasks stay out of pyramid
- large fuzzy tasks escalate into pyramid
- existing-project changes trigger boundary mapping before decomposition

## How to use

1. Start a fresh agent session.
2. Give it the scenario prompt and follow the scenario's skill instruction.
3. Answer clarifying questions as the user for that scenario.
4. When it reports the pyramid is complete, run:

```bash
UV_CACHE_DIR="$PWD/.superpowers/uv-cache" \
UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
UV_INDEX_STRATEGY=unsafe-best-match \
uv run --with pyyaml skills/pyramid-decomposition/tests/evals/run_eval.py <scenario.md>
```

The runner reads workspace-local pyramid state from `.superpowers/pyramid-memory/` and checks the assertions embedded in the scenario file.

## Scenarios

- `01_simple_blog.md`
- `02_ecommerce.md`
- `03_data_pipeline.md`
- `04_simple-task-no-pyramid.md`
- `05_large-task-escalates.md`
- `06_existing-project-routing.md`
