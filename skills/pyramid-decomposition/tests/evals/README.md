# Pyramid Decomposition Evals

These scenarios verify that `pyramid-decomposition` produces a structurally valid pyramid from fuzzy prompts.

## How to use

1. Start a fresh agent session.
2. Give it the scenario prompt and explicitly tell it to use `pyramid-decomposition`.
3. Answer clarifying questions as the user for that scenario.
4. When it reports the pyramid is complete, run:

```bash
uv run --with pyyaml skills/pyramid-decomposition/tests/evals/run_eval.py <scenario.md>
```

The runner exports the project state from `~/.pyramid-memory/` and checks the assertions embedded in the scenario file.

## Scenarios

- `01_simple_blog.md`
- `02_ecommerce.md`
- `03_data_pipeline.md`
