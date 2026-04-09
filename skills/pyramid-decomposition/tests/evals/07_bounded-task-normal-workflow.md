# Eval 07: Bounded Multi-Step Task Uses Normal Workflow

## Initial prompt to give the agent

> Add CSV export to the existing reporting page, including one backend endpoint, one frontend button, and one integration test.

## Skill instruction

> Start with the normal Superpowers workflow and let it choose the correct route.

## Expected outcome (assertions)

```yaml
project_should_exist: false
expect_memory_config: false
project: eval-bounded-07
expected_paths_exist:
  - docs/superpowers/specs/
  - docs/superpowers/plans/
```

## Notes

- This should stay on the bounded normal workflow.
- Correct behavior is to produce normal spec/plan artifacts without activating pyramid decomposition.
